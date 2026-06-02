from pathlib import Path

# Configuraciones
BASE_DIR = Path(__file__).parent # Directorio principal
#DB_PATH = BASE_DIR / "reportes.db" ----- SQL-Lite
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
