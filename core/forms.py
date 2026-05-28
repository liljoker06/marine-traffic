from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


INPUT_CLASS = (
    'w-full bg-gray-800 border border-gray-700 text-white rounded-lg '
    'px-4 py-3 focus:outline-none focus:border-blue-500 placeholder-gray-500'
)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Prénom'}),
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nom'}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'votre@email.com'}),
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'Mot de passe',
        })
        self.fields['password2'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'Confirmer le mot de passe',
        })

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Cette adresse email est déjà utilisée.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        # Génère un username unique à partir de l'email
        base = self.cleaned_data['email'].split('@')[0]
        username = base
        n = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{n}'
            n += 1
        user.username = username
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'votre@email.com',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Mot de passe',
        })
    )


class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Prénom'}),
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nom'}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'votre@email.com'}),
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
