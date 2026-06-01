from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('cambiar-clave/', views.cambiar_clave, name='cambiar_clave'),
    path('gestion-usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('auditoria/', views.auditoria, name='auditoria'),
]