from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegisterForm, LoginForm, UserEditForm


def index(request):
    return render(request, 'core/index.html')


@login_required
def map_view(request):
    return render(request, 'core/map.html')


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


def about_view(request):
    return render(request, 'core/about.html')


def faq_view(request):
    return render(request, 'core/faq.html')


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
