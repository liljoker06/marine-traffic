from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

INPUT_CLASS = (
    'w-full bg-gray-800 border border-gray-700 text-white rounded-lg '
    'px-4 py-3 focus:outline-none focus:border-blue-500 placeholder-gray-500'
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'votre@email.com',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': "Nom d'utilisateur",
            'password1': 'Mot de passe',
            'password2': 'Confirmer le mot de passe',
        }
        for field, placeholder in placeholders.items():
            self.fields[field].widget.attrs.update({
                'class': INPUT_CLASS,
                'placeholder': placeholder,
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': "Nom d'utilisateur",
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Mot de passe',
        })
    )
