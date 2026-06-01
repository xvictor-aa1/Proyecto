AUTH_USER_MODEL = 'usuarios.Usuario'

AUTHENTICATION_BACKENDS = [
    'usuarios.auth_backend.CedulaOrUsernameBackend',
    # 'django.contrib.auth.backends.ModelBackend',  # Opcional pero no necesario
]