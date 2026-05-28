from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

from .forms import RegisterForm, LoginForm, UserEditForm
from .models import Port

# ======================================================
# HOME + MAP

def index(request):
    return render(request, 'core/index.html')

@login_required
def map_view(request):
    return render(request, "core/map.html")


# ======================================================
# PORTS (LISTE + API)

def ports_list(request):
    qs = Port.objects.all()

    search = request.GET.get("search", "").strip()
    country = request.GET.get("country", "").strip()
    harbor_size = request.GET.get("harbor_size", "").strip()

    if search:
        qs = qs.filter(name__icontains=search)
    if country:
        qs = qs.filter(country__iexact=country)
    if harbor_size:
        qs = qs.filter(harbor_size=harbor_size)

    countries = (
        Port.objects.values_list("country", flat=True)
        .distinct()
        .order_by("country")
    )
    harbor_sizes = (
        Port.objects.filter(harbor_size__in=["L", "M", "S", "V"])
        .values_list("harbor_size", flat=True)
        .distinct()
        .order_by("harbor_size")
    )
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "core/ports.html",
        {
            "page_obj": page_obj,
            "countries": countries,
            "harbor_sizes": harbor_sizes,
            "search": search,
            "selected_country": country,
            "selected_harbor_size": harbor_size,
            "total": Port.objects.count(),
        },
    )


def _harbor_size_available():
    """
    vérif si des ports ont un harbor_size renseigné et stock en cache
    """
    if not hasattr(_harbor_size_available, "_cache"):
        _harbor_size_available._cache = Port.objects.filter(
            harbor_size__in=["L", "M", "S", "V"]
        ).exists()
    return _harbor_size_available._cache


def ports_api(request):
    """
    renvoie les ports visibles selon le zoom et la bbox 
    """
    try:
        zoom = min(max(int(request.GET.get("zoom", 10)), 1), 20)
    except (ValueError, TypeError):
        zoom = 10

    bbox = request.GET.get("bbox", "").strip()

    qs = Port.objects.all()

    # filtre bbox (si fourni)
    if bbox:
        # tente de parser la bbox, sinon ignore le filtre
        try:
            south, west, north, east = map(float, bbox.split(","))
            qs = qs.filter(
                latitude__gte=south,
                latitude__lte=north,
                longitude__gte=west,
                longitude__lte=east,
            )
        except (ValueError, TypeError):
            pass

    # si harboz_size présent
    if _harbor_size_available():
        # si zoom petit, on affiche que les grands ports, si zoom moyen on ajoute les moyenss....
        if zoom <= 3:
            qs = qs.filter(harbor_size="L")
        elif zoom <= 5:
            qs = qs.filter(harbor_size__in=["L", "M"])
        elif zoom <= 8:
            qs = qs.filter(harbor_size__in=["L", "M", "S"])
    # sinon sur wpi_number (équivalent d'importance)
    else:
        qs = qs.order_by("wpi_number")
        if zoom <= 3:
            qs = qs[:250]
        elif zoom <= 5:
            qs = qs[:700]
        elif zoom <= 8:
            qs = qs[:2000]

    ports = list(
        qs.values("id", "name", "country", "region", "latitude", "longitude", "harbor_size")
    )
    return JsonResponse({"ports": ports})


# ======================================================
# AUTH

def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Bienvenue {user.username} ! Votre compte a été créé.')
        return redirect('index')

    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        try:
            username = User.objects.get(email=email).username
        except User.DoesNotExist:
            username = None

        user = authenticate(request, username=username, password=password) if username else None

        if user:
            login(request, user)
            messages.success(request, f'Bon retour, {user.username} !')
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Vous avez été déconnecté.')
    return redirect('index')


# ======================================================
# PAGES SIMPLES

def about_view(request):
    return render(request, 'core/about.html')


def faq_view(request):
    return render(request, 'core/faq.html')


# ======================================================
# PROFIL

@login_required
def profile_view(request):
    edit_form = UserEditForm(instance=request.user)
    return render(request, 'core/profile.html', {
        'edit_form': edit_form,
        'show_edit_modal': False,
    })


@login_required
def edit_profile_view(request):
    form = UserEditForm(request.POST or None, instance=request.user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Votre profil a été mis à jour.')
        return redirect('profile')

    return render(request, 'core/profile.html', {
        'edit_form': form,
        'show_edit_modal': True,
    })