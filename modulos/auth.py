from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from database import get_db, verificar_login, crear_usuario
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from functools import wraps
from config import LOGO_ALCALDIA, LOGO_INFO
import base64
auth_bp = Blueprint('auth', __name__)


# ---------------------------------------------------------------------------------------------------------------------------
#   Gestion de Usuarios
#
#   [agregar / modificar / eliminar]
#
#   Nota: Actualmente falta un Dashboard para la administracion de los usuairos
#   pero el codigo funciona correctamente
#
# ---------------------------------------------------------------------------------------------------------------------------  
#
#       Superadmin: Control total sobre los demas, crear a otros admins, usuarios, y modificar los valores de los
#       valores de los otros usuarios.
#
#       Admin: Crea, altear, modifica o elimina los datoos de los usuarios, pero su nivel de permisos sobre la base de datos
#       no es absoluta como el Superadmin.
#
#       Usuario: Usuario normal, solo puede cambiar su propia conotraseña
#
# ---------------------------------------------------------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"error": "no_auth"}), 401
        return f(*args, **kwargs)
    return decorated

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        data = request.json or {}
        cedula = data.get("cedula","")
        password = data.get("password","")
        user = verificar_login(cedula, password)
        if user:
            session["logged_in"] = True
            session["user_id"] = user["id"]
            session["rol_usuario"] = user["rol"]
            session["nombre_usuario"] = user["nombre_completo"]
            db = get_db()
            db.execute("UPDATE usuarios SET ultimo_login = ? WHERE id = ?",
                       (datetime.datetime.now().isoformat(), user["id"]))
            db.commit()
            db.close()
            return jsonify({"ok": True, "rol": user["rol"], "nombre": user["nombre_completo"]})
        else:
            return jsonify({"error": "Cédula o contraseña incorrecta"}), 401
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

@auth_bp.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))
    return render_template("index.html", rol=session.get("rol_usuario","usuario"), nombre=session.get("nombre_usuario",""))

@auth_bp.route("/api/me")
def me():
    if not session.get("logged_in"):
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "rol": session.get("rol_usuario"), "nombre": session.get("nombre_usuario")})

@auth_bp.route("/api/logos")
def get_logos():
    result = {}
    for nombre, path in [("alcaldia", LOGO_ALCALDIA), ("informatica", LOGO_INFO)]:
        if path.exists():
            ext = path.suffix.lower().replace('.','')
            mime = 'jpeg' if ext in ('jpg','jpeg') else ext
            with open(path,'rb') as f:
                result[nombre] = f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"
        else:
            result[nombre] = ""
    return jsonify(result)

@auth_bp.route("/api/usuarios", methods=["GET"])
@login_required
def listar_usuarios():
    rol_actual = session.get("rol_usuario")
    if rol_actual not in ("superadmin", "admin"):
        return jsonify({"error": "No autorizado"}), 403
    db = get_db()
    if rol_actual == "superadmin":
        rows = db.execute("SELECT id, cedula, nombre_completo, cargo, rol, ultimo_login FROM usuarios ORDER BY rol, nombre_completo").fetchall()
    else:
        rows = db.execute("SELECT id, cedula, nombre_completo, cargo, rol, ultimo_login FROM usuarios WHERE rol = 'usuario' ORDER BY nombre_completo").fetchall()
    db.close()
    return jsonify(rows)  # rows son dict gracias a dictionary=True

@auth_bp.route("/api/usuarios", methods=["POST"])
@login_required
def crear_usuario_api():
    rol_actual = session.get("rol_usuario")
    data = request.json or {}
    cedula = data.get("cedula")
    nombre = data.get("nombre_completo")
    cargo = data.get("cargo", "")
    password = data.get("password")
    rol = data.get("rol", "usuario")
    if not cedula or not nombre or not password:
        return jsonify({"error": "Faltan campos obligatorios"}), 400
    if rol_actual == "superadmin":
        if rol not in ("superadmin", "admin", "usuario"):
            return jsonify({"error": "Rol inválido"}), 400
        if rol == "superadmin":
            db = get_db()
            count = db.execute("SELECT COUNT(*) as cnt FROM usuarios WHERE rol = 'superadmin'").fetchone()["cnt"]
            db.close()
            if count > 0:
                return jsonify({"error": "Ya existe un superadmin"}), 409
    elif rol_actual == "admin":
        if rol != "usuario":
            return jsonify({"error": "Solo puedes crear usuarios regulares"}), 403
    else:
        return jsonify({"error": "No autorizado"}), 403
    if crear_usuario(cedula, nombre, cargo, password, rol):
        return jsonify({"ok": True})
    else:
        return jsonify({"error": "La cédula ya existe"}), 409

@auth_bp.route("/api/usuarios/<int:uid>", methods=["PUT"])
@login_required
def actualizar_usuario(uid):
    rol_actual = session.get("rol_usuario")
    data = request.json or {}
    db = get_db()
    user = db.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()
    if not user:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
    if rol_actual == "superadmin":
        pass
    elif rol_actual == "admin":
        if user["rol"] != "usuario":
            db.close()
            return jsonify({"error": "No puedes modificar administradores"}), 403
    else:
        db.close()
        return jsonify({"error": "No autorizado"}), 403
    if uid == session.get("user_id") and rol_actual == "superadmin":
        nuevo_rol = data.get("rol", user["rol"])
        if nuevo_rol != "superadmin":
            count = db.execute("SELECT COUNT(*) as cnt FROM usuarios WHERE rol = 'superadmin'").fetchone()["cnt"]
            if count <= 1:
                db.close()
                return jsonify({"error": "No puedes cambiar tu rol, eres el único superadmin"}), 403
    campos = {}
    if "cedula" in data: campos["cedula"] = data["cedula"]
    if "nombre_completo" in data: campos["nombre_completo"] = data["nombre_completo"]
    if "cargo" in data: campos["cargo"] = data["cargo"]
    if "password" in data and data["password"]:
        campos["password_hash"] = generate_password_hash(data["password"])
    if "rol" in data:
        nuevo_rol = data["rol"]
        if nuevo_rol not in ("superadmin", "admin", "usuario"):
            db.close()
            return jsonify({"error": "Rol inválido"}), 400
        if nuevo_rol == "superadmin" and rol_actual == "superadmin":
            if user["rol"] != "superadmin":
                count = db.execute("SELECT COUNT(*) as cnt FROM usuarios WHERE rol = 'superadmin'").fetchone()["cnt"]
                if count > 0:
                    db.close()
                    return jsonify({"error": "Ya existe un superadmin"}), 409
        elif rol_actual == "admin":
            if nuevo_rol != "usuario":
                db.close()
                return jsonify({"error": "No puedes asignar ese rol"}), 403
        campos["rol"] = nuevo_rol
    if campos:
        sets = ", ".join([f"{k}=?" for k in campos])
        valores = list(campos.values()) + [uid]
        try:
            db.execute(f"UPDATE usuarios SET {sets} WHERE id=?", valores)
            db.commit()
        except mysql.connector.IntegrityError:
            db.close()
            return jsonify({"error": "La cédula ya existe"}), 409
    db.close()
    return jsonify({"ok": True})

@auth_bp.route("/api/usuarios/<int:uid>", methods=["DELETE"])
@login_required
def eliminar_usuario(uid):
    rol_actual = session.get("rol_usuario")
    if uid == session.get("user_id"):
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 403
    db = get_db()
    user = db.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()
    if not user:
        db.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
    if rol_actual == "superadmin":
        if user["rol"] == "superadmin":
            count = db.execute("SELECT COUNT(*) as cnt FROM usuarios WHERE rol = 'superadmin'").fetchone()["cnt"]
            if count <= 1:
                db.close()
                return jsonify({"error": "No puedes eliminar al único superadmin"}), 403
    elif rol_actual == "admin":
        if user["rol"] != "usuario":
            db.close()
            return jsonify({"error": "No puedes eliminar administradores"}), 403
    else:
        db.close()
        return jsonify({"error": "No autorizado"}), 403
    db.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    db.commit()
    db.close()
    return jsonify({"ok": True})

@auth_bp.route("/api/usuarios/me/password", methods=["PUT"])
@login_required
def cambiar_password():
    data = request.json or {}
    current = data.get("current_password")
    new = data.get("new_password")
    if not current or not new:
        return jsonify({"error": "Faltan campos"}), 400
    db = get_db()
    user = db.execute("SELECT * FROM usuarios WHERE id=?", (session["user_id"],)).fetchone()
    if not user or not check_password_hash(user["password_hash"], current):
        db.close()
        return jsonify({"error": "Contraseña actual incorrecta"}), 403
    db.execute("UPDATE usuarios SET password_hash=? WHERE id=?", (generate_password_hash(new), session["user_id"]))
    db.commit()
    db.close()
    return jsonify({"ok": True})
