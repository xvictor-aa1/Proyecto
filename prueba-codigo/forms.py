from django import forms
from django.core.validators import MinLengthValidator, RegexValidator
from .models import Usuario
from .validators import no_reuse_password
import re

def validar_contrasena(value):
    if len(value) < 6:
        raise forms.ValidationError("La contraseña debe tener al menos 6 caracteres.")
    if len(re.findall(r'[^a-zA-Z0-9]', value)) < 2:
        raise forms.ValidationError("La contraseña debe contener al menos 2 caracteres especiales.")

class LoginForm(forms.Form):
    usuario_cedula = forms.CharField(label='Usuario o Cédula')
    password = forms.CharField(widget=forms.PasswordInput)

class CambioClaveForm(forms.Form):
    password_actual = forms.CharField(widget=forms.PasswordInput, label='Contraseña actual')
    password_nueva = forms.CharField(widget=forms.PasswordInput, label='Nueva contraseña', validators=[validar_contrasena])
    confirmar_password = forms.CharField(widget=forms.PasswordInput, label='Confirmar nueva contraseña')

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password_nueva')
        p2 = cleaned_data.get('confirmar_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas nuevas no coinciden.")
        return cleaned_data

class CrearUsuarioForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, validators=[validar_contrasena])
    confirmar_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ['username', 'nombre', 'apellido', 'cedula', 'rol']

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirmar_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        # Validar contraseña no repetida entre usuarios
        if p1:
            no_reuse_password(p1, exclude_user_id=None)
        return cleaned