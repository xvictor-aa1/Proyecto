import datetime
import shutil
import os
import zipfile
from pathlib import Path
from config import BACKUP_CONFIG, BASE_DIR, DB_CONFIG

# Modulo de Backups de Respaldo para el Sistema
#
# Comandos de CMD:
#
#   para un backup completo:
#       python app.py -backup general
#
#   Para un backup de base de datos:
#       python app.py -database
#
#   Para un backup de configuraciones:
#       python app.py -config
#
#   Para un backup de integridad del codigo del sistema:
#       python app.py -integridad
#

def _backup_dir():
    backup_dir = Path(BACKUP_CONFIG["backup_dir"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def _limpiar_antiguos(backup_dir):
    """Elimina backups más antiguos que retain_days días."""
    retain_days = BACKUP_CONFIG.get("retain_days", 0)
    if retain_days <= 0:
        return
    ahora = datetime.datetime.now()
    for f in backup_dir.iterdir():
        if f.is_file():
            try:
                mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                if (ahora - mtime).days > retain_days:
                    f.unlink()
            except:
                pass

def backup_config():
    """Respalda el archivo config.py y cualquier .env."""
    backup_dir = _backup_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = backup_dir / f"config_backup_{timestamp}.zip"
    with zipfile.ZipFile(archivo_salida, 'w', zipfile.ZIP_DEFLATED) as zipf:
        config_file = BASE_DIR / "config.py"
        if config_file.exists():
            zipf.write(config_file, config_file.name)
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            zipf.write(env_file, env_file.name)
    _limpiar_antiguos(backup_dir)
    return archivo_salida

def backup_database():
    """Respalda la base de datos MySQL usando Python (dump SQL)."""
    import mysql.connector
    from config import DB_CONFIG
    backup_dir = _backup_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = backup_dir / f"database_backup_{timestamp}.sql.zip"
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    # Obtener todas las tablas
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    sql_content = []
    for table in tables:
        # Estructura de la tabla
        cursor.execute(f"SHOW CREATE TABLE `{table}`")
        create_stmt = cursor.fetchone()[1]
        sql_content.append(f"{create_stmt};\n\n")
        # Datos
        cursor.execute(f"SELECT * FROM `{table}`")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        for row in rows:
            values = []
            for val in row:
                if val is None:
                    values.append("NULL")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    values.append(f"'{str(val).replace(chr(39), chr(39)+chr(39))}'")
            sql_content.append(f"INSERT INTO `{table}` (`{'`, `'.join(columns)}`) VALUES ({', '.join(values)});\n")
        sql_content.append("\n")
    cursor.close()
    conn.close()
    with zipfile.ZipFile(archivo_salida, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(f"backup_{timestamp}.sql", ''.join(sql_content))
    _limpiar_antiguos(backup_dir)
    return archivo_salida

def backup_code():
    """Respalda los archivos del sistema (código fuente, templates, static)."""
    backup_dir = _backup_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = backup_dir / f"code_backup_{timestamp}.zip"
    exclude_dirs = {"__pycache__", "logs", "backups", "venv", "env", ".git", "node_modules"}
    with zipfile.ZipFile(archivo_salida, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Excluir carpetas que no interesan
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            for file in files:
                full_path = Path(root) / file
                arcname = full_path.relative_to(BASE_DIR)
                zipf.write(full_path, arcname)
    _limpiar_antiguos(backup_dir)
    return archivo_salida

def backup_general():
    """Realiza los tres backups anteriores."""
    b1 = backup_config()
    b2 = backup_database()
    b3 = backup_code()
    return [b1, b2, b3]
