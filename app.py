"""
Sistema de Recepción de Equipos
Coordinación de Informática - Alcaldía Bolivariana de Carlos Arvelo
VERSION - User login
"""
from flask import Flask
# Configuracioon principal de los Modulos del Sistema
from config import SECRET_KEY, BASE_DIR, LOGO_ALCALDIA, LOGO_INFO
# Modulo de Base de Datos MySQL - MariaDB (phpMyAdmin)
from database import init_db, get_db, crear_usuario 
# Modulo de administracion de Usuarios
from modulos.auth import auth_bp
# Modulo de funcion de auditorias
from modulos.auditoria import auditoria_bp
app.register_blueprint(auditoria_bp, url_prefix='/api')
# Sistema de Reportes
from modulos.reportes import reportes_bp 
# Sistme del Servicio de Reportes
from modulos.servicios import servicios_bp
import shutil

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(auth_bp)
app.register_blueprint(reportes_bp, url_prefix='/api')
app.register_blueprint(servicios_bp, url_prefix='/api')

if __name__ == "__main__":
    init_db()
    conn = get_db()
    existe = conn.execute("SELECT id FROM usuarios WHERE cedula = '12345678'").fetchone()
    if not existe:
        crear_usuario('12345678', 'Root', 'Superadmin', 'Admin@2026', 'superadmin')
        print("Usuario superadmin creado: cédula 12345678 / contraseña Admin@2026")
    conn.close()
    (BASE_DIR / "static" / "img").mkdir(parents=True, exist_ok=True)
    for src, dst in [
        (BASE_DIR/"logo_alcaldia.jpeg", LOGO_ALCALDIA),
        (BASE_DIR/"logo_informatica.jpeg", LOGO_INFO),
    ]:
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
    print("="*55)
    print("  Alcaldía Carlos Arvelo - Sistema de Reportes v5.0 (Rol User-Login/ Codigo ahora segmentado en modulos para ajustes rapidos)")
    print("  Abrir en: http://localhost:5000")
    print("="*55)
    app.run(debug=True, port=5000, host='0.0.0.0')
