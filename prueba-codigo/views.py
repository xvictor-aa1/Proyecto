from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden
from .models import Usuario
from .forms import LoginForm, CambioClaveForm, CrearUsuarioForm
from .validators import no_reuse_password
from .models import Auditoria  # ver abajo
from functools import wraps

# Decorador para roles
def rol_requerido(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.rol not in roles:
                return HttpResponseForbidden("No tienes permiso para acceder a esta página.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Modelo Auditoria (agregar en models.py)
class Auditoria(models.Model):
    admin = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='acciones')
    accion = models.CharField(max_length=20)
    usuario_afectado = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='acciones_recibidas')
    detalle = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

# ------------------------ VISTAS -------------------------

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import authenticate
            usuario_cedula = form.cleaned_data['usuario_cedula']
            password = form.cleaned_data['password']
            user = authenticate(request, username=usuario_cedula, password=password)
            if user is not None:
                login(request, user)
                user.ultimo_login = timezone.now()
                user.save()
                messages.success(request, f'Bienvenido, {user.username}')
                return redirect('dashboard')
            else:
                messages.error(request, 'Credenciales incorrectas.')
    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    # Redirige según rol o muestra panel común
    return render(request, 'usuarios/dashboard.html', {'user': request.user})

@login_required
def cambiar_clave(request):
    if request.method == 'POST':
        form = CambioClaveForm(request.POST)
        if form.is_valid():
            actual = form.cleaned_data['password_actual']
            nueva = form.cleaned_data['password_nueva']
            user = request.user
            if not user.check_password(actual):
                messages.error(request, 'Contraseña actual incorrecta.')
            else:
                # Validar no reutilización (comparar con otros usuarios excepto él mismo)
                try:
                    no_reuse_password(nueva, exclude_user_id=user.id)
                except ValidationError as e:
                    messages.error(request, e.message)
                    return render(request, 'usuarios/cambiar_clave.html', {'form': form})
                
                user.set_password(nueva)
                user.save()
                update_session_auth_hash(request, user)  # Mantiene la sesión
                Auditoria.objects.create(
                    admin=user, accion='cambio_clave', usuario_afectado=user,
                    detalle='Cambió su propia contraseña'
                )
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('dashboard')
    else:
        form = CambioClaveForm()
    return render(request, 'usuarios/cambiar_clave.html', {'form': form})

@login_required
@rol_requerido('superadmin', 'admin')
def gestion_usuarios(request):
    es_super = request.user.rol == 'superadmin'
    if es_super:
        usuarios = Usuario.objects.all()
    else:
        usuarios = Usuario.objects.filter(rol='usuario')  # Solo puede ver usuarios normales

    if request.method == 'POST':
        if 'crear_usuario' in request.POST:
            form = CrearUsuarioForm(request.POST)
            if form.is_valid():
                # Validar que no se pueda crear superadmin desde aquí
                if form.cleaned_data['rol'] == 'superadmin':
                    messages.error(request, 'No se puede crear un SuperAdmin desde esta interfaz.')
                    return redirect('gestion_usuarios')
                # Admin solo puede crear usuarios
                if not es_super and form.cleaned_data['rol'] != 'usuario':
                    messages.error(request, 'No tienes permiso para crear ese tipo de usuario.')
                    return redirect('gestion_usuarios')

                nuevo_user = form.save(commit=False)
                nuevo_user.set_password(form.cleaned_data['password'])
                nuevo_user.save()
                Auditoria.objects.create(
                    admin=request.user, accion='crear', usuario_afectado=nuevo_user,
                    detalle=f"Creó usuario {nuevo_user.username} (Cédula: {nuevo_user.cedula}, Rol: {nuevo_user.get_rol_display()})"
                )
                messages.success(request, 'Usuario creado exitosamente.')
                return redirect('gestion_usuarios')
        elif 'eliminar_usuario' in request.POST:
            user_id = request.POST.get('user_id')
            try:
                user_a_eliminar = Usuario.objects.get(pk=user_id)
            except:
                messages.error(request, 'Usuario no encontrado.')
                return redirect('gestion_usuarios')
            if user_a_eliminar == request.user:
                messages.error(request, 'No puedes eliminarte a ti mismo.')
                return redirect('gestion_usuarios')
            if not es_super and user_a_eliminar.rol != 'usuario':
                messages.error(request, 'No puedes eliminar a ese usuario.')
                return redirect('gestion_usuarios')
            if es_super and user_a_eliminar.rol == 'superadmin':
                messages.error(request, 'No puedes eliminar al SuperAdmin.')
                return redirect('gestion_usuarios')
            # Auditoría
            Auditoria.objects.create(
                admin=request.user, accion='eliminar', usuario_afectado=user_a_eliminar,
                detalle=f"Eliminó a {user_a_eliminar.username} (Cédula: {user_a_eliminar.cedula})"
            )
            user_a_eliminar.delete()
            messages.success(request, 'Usuario eliminado.')
            return redirect('gestion_usuarios')
    else:
        form = CrearUsuarioForm()
        # Filtrar roles disponibles
        if not es_super:
            form.fields['rol'].choices = [('usuario', 'Usuario')]  # Solo puede crear usuario
        else:
            form.fields['rol'].choices = [('admin', 'Admin'), ('usuario', 'Usuario')]

    return render(request, 'usuarios/gestion_usuarios.html', {
        'form': form,
        'usuarios': usuarios,
        'es_super': es_super
    })

@login_required
@rol_requerido('superadmin', 'admin')
def auditoria(request):
    es_super = request.user.rol == 'superadmin'
    if es_super:
        registros = Auditoria.objects.all().order_by('-fecha')[:100]
    else:
        registros = Auditoria.objects.filter(admin=request.user).order_by('-fecha')[:100]
    return render(request, 'usuarios/auditoria.html', {'registros': registros})