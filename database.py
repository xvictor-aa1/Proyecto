import mysql.connector
from config import DB_CONFIG
from werkzeug.security import generate_password_hash, check_password_hash

# Modulo de Base de Datos del Sistema
#
# Nota: esta parte del codigo esta hecha con el fin de servir como una
# capa de compatibilidad con modulos anteriores debido a que se utilizaba
# SQL-lite, en lugar de MySQL / MariaDB

class Row(dict):
    """
    Diccionario extendido que soporta acceso por índice entero además de por clave.
    """
    def __init__(self, row_dict, columns):
        super().__init__(row_dict)
        self._tuple = tuple(row_dict[col[0]] for col in columns) if columns else ()

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._tuple[key]
        return super().__getitem__(key)

class Database:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor(dictionary=True)

    def execute(self, query, params=None):
        # reemplazar '?' por '%s' para compatibilidad con MySQL
        query = query.replace('?', '%s')
        self.cursor.execute(query, params or ())
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()

# ------------------------------------------------------------------------------------------------------------
#
#   Tablas de Bases de Datos - MySQL
#
#   Nota: simplificada la tabla de usuario en una nueva separada en formato 3FN,
#   cedulas no pueden repetirse, y el sistema de rol de Usuario 
#
# ------------------------------------------------------------------------------------------------------------

def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return Database(conn)

# Crear tablas de Base de Datos si no existen
# usando parametros previamente establecidos
# en DB_CONFIG
def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    # AGREGAR TABLAS EN MYSQL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cedula VARCHAR(20) UNIQUE NOT NULL,
            nombre_completo VARCHAR(150) NOT NULL,
            cargo VARCHAR(100),
            password_hash VARCHAR(255) NOT NULL,
            rol ENUM('superadmin','admin','usuario') NOT NULL DEFAULT 'usuario',
            ultimo_login DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reportes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero VARCHAR(50) UNIQUE NOT NULL,
            departamento VARCHAR(100),
            telf VARCHAR(50),
            usuario_equipo VARCHAR(100),
            codigo_bienes VARCHAR(100) DEFAULT '',
            fecha VARCHAR(20),
            tecnico VARCHAR(100),
            equipo VARCHAR(50),
            marca VARCHAR(50),
            modelo VARCHAR(50),
            serial VARCHAR(50),
            chequeo_computador JSON DEFAULT '[]',
            chequeo_laptop JSON DEFAULT '[]',
            chequeo_impresora JSON DEFAULT '[]',
            trabajos JSON DEFAULT '[]',
            otros TEXT,
            estado VARCHAR(30) DEFAULT 'Recibido',
            trimestre VARCHAR(10),
            anio INT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nombre_usuario VARCHAR(150),
            cargo_usuario VARCHAR(100),
            cedula_usuario VARCHAR(20)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reportes_servicio (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero VARCHAR(50) NOT NULL,
            departamento VARCHAR(100),
            fecha VARCHAR(20),
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # ── Tabla auditoría con migración segura ───────────────────────────
    # 1. Crear la tabla si no existe (con la estructura completa)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            usuario VARCHAR(150),
            accion VARCHAR(200) NOT NULL,
            detalles TEXT,
            ip VARCHAR(45)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    try:
        cursor.execute("ALTER TABLE auditoria ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP FIRST")
    except mysql.connector.errors.ProgrammingError:
        pass

    try:
        cursor.execute("CREATE INDEX idx_auditoria_timestamp ON auditoria(timestamp);")
    except mysql.connector.errors.ProgrammingError:
        pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_cedula ON usuarios(cedula);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios(rol);")

    cursor.close()
    conn.close()

def verificar_login(cedula, password):
    db = get_db()
    user = db.execute("SELECT * FROM usuarios WHERE cedula = ?", (cedula,)).fetchone()
    db.close()
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def crear_usuario(cedula, nombre, cargo, password_plain, rol='usuario'):
    db = get_db()
    try:
        db.execute("""
            INSERT INTO usuarios (cedula, nombre_completo, cargo, password_hash, rol)
            VALUES (?, ?, ?, ?, ?)
        """, (cedula, nombre, cargo, generate_password_hash(password_plain), rol))
        db.commit()
        db.close()
        return True
    except mysql.connector.IntegrityError:
        db.close()
        return False

def registrar_auditoria(user_id, accion, detalle=""):
    db = get_db()
    db.execute(
        "INSERT INTO auditoria (user_id, accion, detalle) VALUES (?, ?, ?)",
        (user_id, accion, detalle)
    )
    db.commit()
    db.close()

def insert_audit_log(usuario, accion, detalles, ip=""):
    db = get_db()
    db.execute(
        "INSERT INTO auditoria (usuario, accion, detalles, ip) VALUES (?, ?, ?, ?)",
        (usuario, accion, detalles, ip)
    )
    db.commit()
    db.close()
