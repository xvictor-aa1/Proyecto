from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from .models import Usuario

def no_reuse_password(password, user=None, exclude_user_id=None):
    """
    Verificar que ningún otro usuario (excepto el actual, si se especifica) tenga la misma contraseña.
    Compara usando check_password con cada usuario.
    """
    usuarios = Usuario.objects.all()
    if exclude_user_id:
        usuarios = usuarios.exclude(pk=exclude_user_id)
    for u in usuarios:
        if u.password and check_password(password, u.password):
            raise ValidationError("Esta contraseña ya está siendo utilizada por otro usuario.")