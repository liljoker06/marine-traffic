import json
import urllib.request
import urllib.parse

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_GET

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

from .forms import RegisterForm, LoginForm, UserEditForm
from .models import Port, Ship, ShipPosition, SHIP_TYPE_LABELS, NAV_STATUS_LABELS

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


def ships_api(request):
    """
    Retourne les navires dans la bbox visible, mis à jour dans les 6 dernières heures.
    Fenêtre large pour avoir le maximum de navires dès le chargement.
    """
    from datetime import timedelta
    bbox = request.GET.get('bbox', '')
    cutoff = timezone.now() - timedelta(hours=6)
    qs = Ship.objects.filter(last_update__gte=cutoff)
    if bbox:
        try:
            south, west, north, east = map(float, bbox.split(','))
            qs = qs.filter(
                latitude__gte=south,  latitude__lte=north,
                longitude__gte=west,  longitude__lte=east,
            )
        except (ValueError, TypeError):
            pass
    ships = list(qs.values(
        'mmsi', 'name', 'ship_type', 'flag',
        'latitude', 'longitude', 'speed', 'course', 'heading', 'status'
    ))
    return JsonResponse({'ships': ships})


def ship_track_api(request, mmsi):
    """
    Retourne les 50 dernières positions d'un navire (pour tracer sa route).
    """
    try:
        ship = Ship.objects.get(mmsi=mmsi)
    except Ship.DoesNotExist:
        return JsonResponse({'ship': None, 'positions': []})

    positions = list(
        ship.positions
        .values('latitude', 'longitude', 'speed', 'timestamp')[:50]
    )
    return JsonResponse({
        'ship': {
            'mmsi':       ship.mmsi,
            'name':       ship.name,
            'ship_type':  ship.ship_type,
            'type_label': SHIP_TYPE_LABELS.get(ship.ship_type, 'Autre'),
            'status':     ship.status,
            'status_label': NAV_STATUS_LABELS.get(ship.status, 'Indéfini'),
            'speed':      ship.speed,
            'course':     ship.course,
            'flag':       ship.flag,
        },
        'positions': positions,
    })


def ports_search_api(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"ports": []})
    ports = list(
        Port.objects.filter(name__icontains=q)
        .order_by("name")
        .values("id", "name", "country", "region", "latitude", "longitude", "harbor_size")[:12]
    )
    return JsonResponse({"ports": ports})


# ======================================================
# WIKIPEDIA PROXY

@require_GET
def wikipedia_proxy(request):
    """
    Proxy côté serveur pour l'API Wikipedia.
    Évite les CORS et ajoute un fallback recherche quand le titre exact est inconnu.
    """
    term = request.GET.get("term", "").strip()
    lang = request.GET.get("lang", "fr")
    if not term:
        return JsonResponse({"error": "term required"}, status=400)
    if lang not in ("fr", "en", "es", "de", "it", "pt", "ar", "zh"):
        lang = "fr"

    def _fetch(url):
        req = urllib.request.Request(url, headers={"User-Agent": "MarineTrafficApp/1.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read())

    # 1) Lookup direct par titre
    try:
        data = _fetch(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
            f"{urllib.parse.quote(term, safe='')}"
        )
        if data.get("type") not in ("disambiguation", None) and data.get("extract"):
            return JsonResponse(data)
    except Exception:
        pass

    # 2) Fallback : recherche textuelle puis summary du premier résultat
    try:
        search = _fetch(
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={urllib.parse.quote(term, safe='')}"
            f"&format=json&srlimit=1&origin=*"
        )
        results = search.get("query", {}).get("search", [])
        if results:
            title = results[0]["title"]
            data = _fetch(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
                f"{urllib.parse.quote(title, safe='')}"
            )
            if data.get("extract"):
                return JsonResponse(data)
    except Exception:
        pass

    return JsonResponse({"error": "not found"}, status=404)


# ======================================================
# SHIP PHOTO (Wikimedia Commons)

@require_GET
def ship_photo_proxy(request):
    """
    Cherche une photo du navire sur Wikimedia Commons.
    Essaie plusieurs variantes du nom (MV, MS, Ship...).
    Résultat mis en cache 1h.
    """
    from django.core.cache import cache

    name = request.GET.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "name required"}, status=400)

    cache_key = f"ship_photo_{name.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached) if cached else JsonResponse({"error": "not found"}, status=404)

    # Variantes de recherche — du plus précis au plus générique
    queries = [
        f"{name} ship",
        f"MV {name}",
        f"MS {name}",
        f"SS {name}",
        f"{name} vessel",
        name,
    ]

    def _wikimedia_search(q):
        encoded = urllib.parse.quote(q, safe="")
        req = urllib.request.Request(
            f"https://commons.wikimedia.org/w/api.php"
            f"?action=query&generator=search&gsrnamespace=6"
            f"&gsrsearch={encoded}&prop=imageinfo"
            f"&iiprop=url&iiurlwidth=600&format=json&gsrlimit=10&origin=*",
            headers={"User-Agent": "MarineTrafficApp/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read())

    for q in queries:
        try:
            data  = _wikimedia_search(q)
            pages = data.get("query", {}).get("pages", {})
            for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
                info  = (page.get("imageinfo") or [{}])[0]
                url   = info.get("url", "").lower()
                thumb = info.get("thumburl", "")
                if thumb and not url.endswith(".svg") and not url.endswith(".gif") \
                        and not url.endswith(".ogg") and not url.endswith(".webm"):
                    result = {
                        "url":   info.get("url", ""),
                        "thumb": thumb,
                        "page":  f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(page.get('title',''), safe=':')}",
                    }
                    cache.set(cache_key, result, 3600)
                    return JsonResponse(result)
        except Exception:
            continue

    cache.set(cache_key, None, 3600)
    return JsonResponse({"error": "not found"}, status=404)


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