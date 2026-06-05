"""
Sistema de Recepción de Equipos
Coordinación de Informática - Alcaldía Bolivariana de Carlos Arvelo
VERSION - User login
"""
from flask import Flask
# Configuracioon principal de los Modulos del Sistema
from config import SECRET_KEY, BASE_DIR, LOGO_ALCALDIA, LOGO_INFO, BACKUP_CONFIG
# Modulo de Base de Datos MySQL - MariaDB (phpMyAdmin)
from database import init_db, get_db, crear_usuario 
# Modulo de administracion de Usuarios
from modulos.auth import auth_bp
# Sistema de Reportes
from modulos.reportes import reportes_bp 
# Sistema del Servicio de Reportes
from modulos.servicios import servicios_bp
# Modulo de auditoria del sistema
from modulos.audit import log_event
# Funcion de Respaldo - backup del Sistema
from modulos.backup import backup_general, backup_config, backup_database, backup_code
import shutil
import sys
import threading
import time
import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.register_blueprint(auth_bp)
app.register_blueprint(reportes_bp, url_prefix='/api')
app.register_blueprint(servicios_bp, url_prefix='/api')

def scheduled_backup():
    """Hilo de fondo para backups diarios."""
    while True:
        # Calcular próxima hora de backup
        now = datetime.datetime.now()
        target_time_str = BACKUP_CONFIG.get("daily_time", "02:00")
        target_hour, target_min = map(int, target_time_str.split(':'))
        target = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        sleep_seconds = (target - now).total_seconds()
        time.sleep(sleep_seconds)
        try:
            log_event(None, "Backup automático", "Inicio programado")
            archivos = backup_general()
            log_event(None, "Backup automático completado", f"Archivos: {[str(a) for a in archivos]}")
        except Exception as e:
            log_event(None, "Error en backup automático", str(e))

if __name__ == "__main__":
    # Procesar argumentos de línea de comandos
    if len(sys.argv) > 1 and sys.argv[1] == "-backup":
        if len(sys.argv) < 3:
            print("Uso: python app.py -backup <tipo> (general/config/database/integridad)")
            sys.exit(1)
        tipo = sys.argv[2].lower()
        try:
            if tipo == "general":
                archivos = backup_general()
                print("Backup general completado:", [str(a) for a in archivos])
            elif tipo == "config":
                archivo = backup_config()
                print("Backup de configuración:", archivo)
            elif tipo == "database":
                archivo = backup_database()
                print("Backup de base de datos:", archivo)
            elif tipo == "integridad":
                archivo = backup_code()
                print("Backup de código:", archivo)
            else:
                print("Tipo no válido. Use: general, config, database, integridad")
                sys.exit(1)
        except Exception as e:
            print("Error al realizar backup:", e)
            sys.exit(1)
        sys.exit(0)

    # Iniciar aplicación normal
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

    # Iniciar hilo de backup si está activado
    if BACKUP_CONFIG.get("enabled", False):
        backup_thread = threading.Thread(target=scheduled_backup, daemon=True)
        backup_thread.start()
        log_event(None, "Sistema", "Backup diario iniciado")

    log_event(None, "Inicio del sistema", f"Log de auditoría en {BASE_DIR / 'logs'}")
    print("="*55)
    print("  Alcaldía Carlos Arvelo - Sistema de Reportes v5.0")
    print("  Abrir en: http://localhost:5000")
    print("="*55)
    app.run(debug=False, port=5000, host='0.0.0.0')
