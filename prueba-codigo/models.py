from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator, RegexValidator

class UsuarioManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        # username será la cédula o un alias, aquí dejaremos que se maneje
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'superadmin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

class Usuario(AbstractUser):
    ROLES = (
        ('superadmin', 'SuperAdmin'),
        ('admin', 'Admin'),
        ('usuario', 'Usuario'),
    )
    cedula = models.CharField(max_length=20, unique=True, verbose_name="Cédula")
    rol = models.CharField(max_length=15, choices=ROLES, default='usuario')
    ultimo_login = models.DateTimeField(null=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'cedula', 'rol']

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"