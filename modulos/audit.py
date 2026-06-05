import datetime
from pathlib import Path
from config import AUDIT_CONFIG, BASE_DIR
from database import insert_audit_log

# Modulo de automatizacion de Logs de Auditoria -
# en formato log-xx-xx-xx-xx.txt y Base de Datos
def get_log_path():
    log_dir = AUDIT_CONFIG.get("log_dir", BASE_DIR / "logs")
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    startup = datetime.datetime.now()
    date_str = startup.strftime(AUDIT_CONFIG.get("filename_date_format", "%Y-%m-%d-%H-%M"))
    filename = f"{AUDIT_CONFIG.get('filename_prefix', 'log-')}{date_str}.txt"
    return log_dir / filename

LOG_PATH = get_log_path()

def log_event(username, action, details="", ip=""):
    if not AUDIT_CONFIG.get("enabled", True):
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = username if username else "Sistema"

    # Escritura en archivo de texto
    line = f"[{timestamp}] Usuario: {user} | Acción: {action}"
    if details:
        line += f" | Detalles: {details}"
    line += "\n"
    encoding = AUDIT_CONFIG.get("file_encoding", "utf-8")
    with open(LOG_PATH, "a", encoding=encoding) as f:
        f.write(line)

    # Inserción en base de datos
    if AUDIT_CONFIG.get("db_logging", True):
        try:
            insert_audit_log(user, action, details, ip)
        except Exception as e:
            # Si falla la BD, seguir sin interrumpir la operación
            pass
