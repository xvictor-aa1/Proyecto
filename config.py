from pathlib import Path

# Configuraciones
BASE_DIR = Path(__file__).parent # Directorio principal
DB_PATH = BASE_DIR / "reportes.db" # Base de datos local
LOGO_ALCALDIA = BASE_DIR / "static" / "img" / "logo_alcaldia.jpeg"
LOGO_INFO = BASE_DIR / "static" / "img" / "logo_informatica.jpeg"
SECRET_KEY = "CarlosArvelo_Informatica_2026"

# Base de datos local del Sistema
# MySQL / MariaDB (phpMyAdmin)
#
DB_CONFIG = {
    "host": "localhost",            # IP Servidor de Base de Datos (Localhost)
    "port": 3306,                   # Puerto 
    "user": "root",                 # Credencial de Usuario
    "password": "",                 # Contraseña
    "database": "reportes_db",      # Base de datos previamente existente
    "charset":  "utf8mb4",          #
    "autocommit": True              #
}

# ── AUDITORÍA ──────────────────────────────────────────────────────────
AUDIT_CONFIG = {
    "enabled": True,                          # True = registrar en archivo y BD
    "log_dir": BASE_DIR / "logs",             # carpeta de logs de texto
    "filename_prefix": "log-",                # prefijo del archivo
    "filename_date_format": "%Y-%m-%d-%H-%M", # formato de fecha/hora para el nombre
    "file_encoding": "utf-8",
    "db_logging": True                        # insertar también en tabla auditoria
}

# ── BACKUP AUTOMÁTICO ──────────────────────────────────────────────────
BACKUP_CONFIG = {
    "enabled": True,                          # Activar backup automático diario
    "daily_time": "02:00",                    # Hora del backup (formato HH:MM)
    "backup_dir": BASE_DIR / "backups",
    "retain_days": 0                          # Cuántos días conservar (0 = todos)
}
