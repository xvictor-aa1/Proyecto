"""
Sistema de Recepción de Equipos
Coordinación de Informática - Alcaldía Bolivariana de Carlos Arvelo
VERSION - User login
"""
from flask import Flask, render_template, request, jsonify, send_file, abort, session, redirect, url_for
import sqlite3, os, io, datetime, json, base64
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from functools import wraps

app = Flask(__name__)
app.secret_key = "CarlosArvelo_Informatica_2026"

BASE_DIR      = Path(__file__).parent
DB_PATH       = BASE_DIR / "reportes.db"
LOGO_ALCALDIA = BASE_DIR / "static" / "img" / "logo_alcaldia.jpeg"
LOGO_INFO     = BASE_DIR / "static" / "img" / "logo_informatica.jpeg"
(BASE_DIR / "static" / "img").mkdir(parents=True, exist_ok=True)

DEPARTAMENTOS = [
    "Alcaldía (Despacho)", "Administración y Finanzas", "Catastro",
    "Desarrollo Social", "Desarrollo Urbano", "Dirección General",
    "Hacienda", "Informática", "Instituto de la Mujer",
    "Jurídico", "Obras Públicas", "Planificación",
    "Recursos Humanos", "Registro Civil", "Secretaría General",
    "Servicios Generales", "SUNAP", "IMVICA", "CPNNA", "Turismo", "Otro"
]
TECNICOS = [
    "Carlos García", "María López", "José Martínez",
    "Ana Rodríguez", "Luis Hernández", "Pedro González",
    "Sofía Díaz", "Miguel Pérez"
]

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

# ------------------------------------------------------------------------------------------------------------
#
#   Tabla usuario separada, cedulas no pueden repetirse, y el sistema de rol de Usuario 
#
# ------------------------------------------------------------------------------------------------------------

def init_db():
    con = get_db()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT UNIQUE NOT NULL,
            nombre_completo TEXT NOT NULL,
            cargo TEXT,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'usuario' CHECK(rol IN ('superadmin','admin','usuario')),
            ultimo_login DATETIME
        );

        CREATE TABLE IF NOT EXISTS reportes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            departamento TEXT,
            telf TEXT,
            usuario_equipo TEXT,
            codigo_bienes TEXT DEFAULT '',
            fecha TEXT,
            tecnico TEXT,
            equipo TEXT,
            marca TEXT,
            modelo TEXT,
            serial TEXT,
            chequeo_computador TEXT DEFAULT '[]',
            chequeo_laptop TEXT DEFAULT '[]',
            chequeo_impresora TEXT DEFAULT '[]',
            trabajos TEXT DEFAULT '[]',
            otros TEXT,
            estado TEXT DEFAULT 'Recibido',
            trimestre TEXT,
            anio INTEGER,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            nombre_usuario TEXT,
            cargo_usuario TEXT,
            cedula_usuario TEXT
        );

        CREATE TABLE IF NOT EXISTS reportes_servicio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            departamento TEXT,
            fecha TEXT,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_usuarios_cedula ON usuarios(cedula);
        CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios(rol);
    """)
    try:
        con.execute("ALTER TABLE reportes ADD COLUMN codigo_bienes TEXT DEFAULT ''")
        con.commit()
    except:
        pass
    con.commit()
    con.close()

def verificar_login(cedula, password):
    con = get_db()
    user = con.execute("SELECT * FROM usuarios WHERE cedula = ?", (cedula,)).fetchone()
    con.close()
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def crear_usuario(cedula, nombre, cargo, password_plain, rol='usuario'):
    con = get_db()
    try:
        con.execute("""
            INSERT INTO usuarios (cedula, nombre_completo, cargo, password_hash, rol)
            VALUES (?, ?, ?, ?, ?)
        """, (cedula, nombre, cargo, generate_password_hash(password_plain), rol))
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        con.close()
        return False

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"error": "no_auth"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET","POST"])
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
            con = get_db()
            con.execute("UPDATE usuarios SET ultimo_login = ? WHERE id = ?",
                        (datetime.datetime.now().isoformat(), user["id"]))
            con.commit()
            con.close()
            return jsonify({"ok": True, "rol": user["rol"], "nombre": user["nombre_completo"]})
        else:
            return jsonify({"error": "Cédula o contraseña incorrecta"}), 401
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html", rol=session.get("rol_usuario","usuario"), nombre=session.get("nombre_usuario",""))

@app.route("/api/me")
def me():
    if not session.get("logged_in"):
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "rol": session.get("rol_usuario"), "nombre": session.get("nombre_usuario")})


# ---------------------------------------------------------------------------------------------------------------------------
#   Funcion agregar / modificar / eliminar
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

@app.route("/api/usuarios", methods=["GET"])
@login_required
def listar_usuarios():
    rol_actual = session.get("rol_usuario")
    if rol_actual not in ("superadmin", "admin"):
        return jsonify({"error": "No autorizado"}), 403
    con = get_db()
    if rol_actual == "superadmin":
        rows = con.execute("SELECT id, cedula, nombre_completo, cargo, rol, ultimo_login FROM usuarios ORDER BY rol, nombre_completo").fetchall()
    elif rol_actual == "admin":
        rows = con.execute("SELECT id, cedula, nombre_completo, cargo, rol, ultimo_login FROM usuarios WHERE rol = 'usuario' ORDER BY nombre_completo").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/usuarios", methods=["POST"])
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
            con = get_db()
            count = con.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'superadmin'").fetchone()[0]
            con.close()
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

@app.route("/api/usuarios/<int:uid>", methods=["PUT"])
@login_required
def actualizar_usuario(uid):
    rol_actual = session.get("rol_usuario")
    data = request.json or {}
    con = get_db()
    user = con.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()
    if not user:
        con.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
    user = dict(user)
    if rol_actual == "superadmin":
        pass
    elif rol_actual == "admin":
        if user["rol"] != "usuario":
            con.close()
            return jsonify({"error": "No puedes modificar administradores"}), 403
    else:
        con.close()
        return jsonify({"error": "No autorizado"}), 403
    if uid == session.get("user_id") and rol_actual == "superadmin":
        nuevo_rol = data.get("rol", user["rol"])
        if nuevo_rol != "superadmin":
            count = con.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'superadmin'").fetchone()[0]
            if count <= 1:
                con.close()
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
            con.close()
            return jsonify({"error": "Rol inválido"}), 400
        if nuevo_rol == "superadmin" and rol_actual == "superadmin":
            if user["rol"] != "superadmin":
                count = con.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'superadmin'").fetchone()[0]
                if count > 0:
                    con.close()
                    return jsonify({"error": "Ya existe un superadmin"}), 409
        elif rol_actual == "admin":
            if nuevo_rol != "usuario":
                con.close()
                return jsonify({"error": "No puedes asignar ese rol"}), 403
        campos["rol"] = nuevo_rol
    if campos:
        sets = ", ".join([f"{k}=?" for k in campos])
        valores = list(campos.values()) + [uid]
        try:
            con.execute(f"UPDATE usuarios SET {sets} WHERE id=?", valores)
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return jsonify({"error": "La cédula ya existe"}), 409
    con.close()
    return jsonify({"ok": True})


@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
@login_required
def eliminar_usuario(uid):
    rol_actual = session.get("rol_usuario")
    if uid == session.get("user_id"):
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 403
    con = get_db()
    user = con.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()
    if not user:
        con.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
    user = dict(user)
    if rol_actual == "superadmin":
        if user["rol"] == "superadmin":
            count = con.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'superadmin'").fetchone()[0]
            if count <= 1:
                con.close()
                return jsonify({"error": "No puedes eliminar al único superadmin"}), 403
    elif rol_actual == "admin":
        if user["rol"] != "usuario":
            con.close()
            return jsonify({"error": "No puedes eliminar administradores"}), 403
    else:
        con.close()
        return jsonify({"error": "No autorizado"}), 403
    con.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    con.commit()
    con.close()
    return jsonify({"ok": True})

@app.route("/api/usuarios/me/password", methods=["PUT"])
@login_required
def cambiar_password():
    data = request.json or {}
    current = data.get("current_password")
    new = data.get("new_password")
    if not current or not new:
        return jsonify({"error": "Faltan campos"}), 400
    con = get_db()
    user = con.execute("SELECT * FROM usuarios WHERE id=?", (session["user_id"],)).fetchone()
    if not user or not check_password_hash(user["password_hash"], current):
        con.close()
        return jsonify({"error": "Contraseña actual incorrecta"}), 403
    con.execute("UPDATE usuarios SET password_hash=? WHERE id=?", (generate_password_hash(new), session["user_id"]))
    con.commit()
    con.close()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------------------------------------------------------
#   Fin de la linea
# ---------------------------------------------------------------------------------------------------------------------------

@app.route("/api/departamentos")
def get_departamentos():
    return jsonify(DEPARTAMENTOS)

@app.route("/api/tecnicos")
def get_tecnicos():
    return jsonify(TECNICOS)

@app.route("/api/logos")
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

@app.route("/api/reportes", methods=["GET"])
@login_required
def listar():
    dpto = request.args.get("departamento","")
    tri  = request.args.get("trimestre","")
    busq = request.args.get("buscar","")
    anio = request.args.get("anio","")
    con  = get_db()
    q    = "SELECT * FROM reportes WHERE 1=1"
    p    = []
    if dpto: q+=" AND departamento=?"; p.append(dpto)
    if tri:  q+=" AND trimestre=?";    p.append(tri)
    if anio: q+=" AND anio=?";         p.append(int(anio))
    if busq: q+=" AND (numero LIKE ? OR departamento LIKE ? OR modelo LIKE ? OR serial LIKE ?)"; p+=[f"%{busq}%"]*4
    q+=" ORDER BY fecha_registro DESC"
    rows=[dict(r) for r in con.execute(q,p)]
    con.close()
    return jsonify(rows)

@app.route("/api/reportes/<int:rid>", methods=["GET"])
@login_required
def obtener(rid):
    con=get_db()
    r=con.execute("SELECT * FROM reportes WHERE id=?",(rid,)).fetchone()
    con.close()
    if not r: abort(404)
    return jsonify(dict(r))

@app.route("/api/reportes", methods=["POST"])
@login_required
def crear():
    d=request.json
    if not d.get("numero"):
        return jsonify({"error":"El número de reporte es obligatorio"}),400
    hoy=datetime.date.today()
    mes=hoy.month
    tri="T1" if mes<=3 else "T2" if mes<=6 else "T3" if mes<=9 else "T4"
    con=get_db()
    try:
        con.execute("""
            INSERT INTO reportes
            (numero,departamento,telf,usuario_equipo,codigo_bienes,fecha,tecnico,equipo,marca,modelo,serial,
             chequeo_computador,chequeo_laptop,chequeo_impresora,trabajos,otros,
             nombre_usuario,cargo_usuario,cedula_usuario,estado,trimestre,anio)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,(d["numero"],d.get("departamento",""),d.get("telf",""),d.get("usuario_equipo",""),
             d.get("codigo_bienes",""),
             d.get("fecha",hoy.strftime("%d-%m-%y")),d.get("tecnico",""),
             d.get("equipo",""),d.get("marca",""),d.get("modelo",""),d.get("serial",""),
             json.dumps(d.get("chequeo_computador",[])),
             json.dumps(d.get("chequeo_laptop",[])),
             json.dumps(d.get("chequeo_impresora",[])),
             json.dumps(d.get("trabajos",[])),
             d.get("otros",""),d.get("nombre_usuario",""),d.get("cargo_usuario",""),
             d.get("cedula_usuario",""),
             d.get("estado","Recibido"),d.get("trimestre",tri),d.get("anio",hoy.year)))
        con.commit()
        nid=con.execute("SELECT id FROM reportes WHERE numero=?",(d["numero"],)).fetchone()[0]
        con.close()
        return jsonify({"ok":True,"id":nid})
    except sqlite3.IntegrityError:
        con.close()
        return jsonify({"error":f"El N° {d['numero']} ya existe"}),409

@app.route("/api/reportes/<int:rid>", methods=["PUT"])
@login_required
def actualizar(rid):
    d=request.json
    hoy=datetime.date.today()
    mes=hoy.month
    tri="T1" if mes<=3 else "T2" if mes<=6 else "T3" if mes<=9 else "T4"
    con=get_db()
    con.execute("""
        UPDATE reportes SET
        departamento=?,telf=?,usuario_equipo=?,codigo_bienes=?,fecha=?,tecnico=?,equipo=?,marca=?,modelo=?,serial=?,
        chequeo_computador=?,chequeo_laptop=?,chequeo_impresora=?,trabajos=?,otros=?,
        nombre_usuario=?,cargo_usuario=?,cedula_usuario=?,estado=?,
        trimestre=?,anio=?
        WHERE id=?
    """,(d.get("departamento",""),d.get("telf",""),d.get("usuario_equipo",""),
         d.get("codigo_bienes",""),
         d.get("fecha",hoy.strftime("%d-%m-%y")),
         d.get("tecnico",""),d.get("equipo",""),d.get("marca",""),d.get("modelo",""),d.get("serial",""),
         json.dumps(d.get("chequeo_computador",[])),
         json.dumps(d.get("chequeo_laptop",[])),
         json.dumps(d.get("chequeo_impresora",[])),
         json.dumps(d.get("trabajos",[])),
         d.get("otros",""),d.get("nombre_usuario",""),d.get("cargo_usuario",""),
         d.get("cedula_usuario",""),
         d.get("estado","Recibido"),d.get("trimestre",tri),d.get("anio",hoy.year),rid))
    con.commit(); con.close()
    return jsonify({"ok":True})

@app.route("/api/reportes/<int:rid>", methods=["DELETE"])
@login_required
def eliminar(rid):
    if session.get("rol_usuario") != "superadmin":
        return jsonify({"error":"Solo el administrador puede eliminar reportes"}),403
    con=get_db()
    con.execute("DELETE FROM reportes WHERE id=?",(rid,))
    con.commit(); con.close()
    return jsonify({"ok":True})

@app.route("/api/resumen")
@login_required
def resumen():
    tri =request.args.get("trimestre","T1")
    anio=int(request.args.get("anio",datetime.date.today().year))
    con=get_db(); p=(tri,anio)
    total =con.execute("SELECT COUNT(*) FROM reportes WHERE trimestre=? AND anio=?",p).fetchone()[0]
    dptos =[(r[0],r[1]) for r in con.execute("SELECT departamento,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY departamento ORDER BY COUNT(*) DESC",p)]
    equipos=[(r[0],r[1]) for r in con.execute("SELECT equipo,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY equipo ORDER BY COUNT(*) DESC",p)]
    modelos=[(r[0]+' '+r[1],r[2]) for r in con.execute("SELECT marca,modelo,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY marca,modelo ORDER BY COUNT(*) DESC",p)]
    estados=[(r[0],r[1]) for r in con.execute("SELECT estado,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY estado ORDER BY COUNT(*) DESC",p)]
    con.close()
    return jsonify({"total":total,"dptos":dptos,"equipos":equipos,"modelos":modelos,"estados":estados})

@app.route("/api/reporte_servicio", methods=["GET"])
@login_required
def listar_servicio():
    con=get_db()
    rows=[dict(r) for r in con.execute("SELECT * FROM reportes_servicio ORDER BY fecha_registro DESC")]
    con.close()
    return jsonify(rows)

@app.route("/api/reporte_servicio", methods=["POST"])
@login_required
def crear_servicio():
    d=request.json
    if not d.get("numero"):
        return jsonify({"error":"El número es obligatorio"}),400
    con=get_db()
    con.execute("INSERT INTO reportes_servicio (numero,departamento,fecha) VALUES(?,?,?)",
                (d["numero"],d.get("departamento",""),d.get("fecha",datetime.date.today().strftime("%d-%m-%y"))))
    con.commit()
    rid=con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.close()
    return jsonify({"ok":True,"id":rid})

@app.route("/api/reporte_servicio/<int:rid>", methods=["DELETE"])
@login_required
def eliminar_servicio(rid):
    con=get_db()
    con.execute("DELETE FROM reportes_servicio WHERE id=?",(rid,))
    con.commit(); con.close()
    return jsonify({"ok":True})

@app.route("/api/pdf_servicio_blank")
@login_required
def pdf_servicio_blank():
    buf=generar_pdf_servicio_blank()
    return send_file(buf,mimetype="application/pdf",as_attachment=True,
                     download_name="ReporteServicio_Blank.pdf")

@app.route("/api/siguiente_numero_servicio")
@login_required
def siguiente_numero_servicio():
    con=get_db()
    anio=datetime.date.today().year
    rows=con.execute("SELECT numero FROM reportes_servicio WHERE fecha_registro LIKE ?",
                     (f"{anio}%",)).fetchall()
    nums=[int(r[0].split('-')[1].split('/')[0]) for r in rows if r[0] and '-' in r[0]]
    siguiente=max(nums)+1 if nums else 1
    con.close()
    return jsonify({"numero":f"RS-{siguiente:03d}/{str(anio)[2:]}"})

@app.route("/api/pdf/<int:rid>")
@login_required
def pdf_reporte(rid):
    con=get_db()
    row=con.execute("SELECT * FROM reportes WHERE id=?",(rid,)).fetchone()
    con.close()
    if not row: abort(404)
    r=dict(row)
    buf=generar_pdf(r)
    nombre=f"Recepcion_{r['numero'].replace('/','_')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)

@app.route("/api/pdf_resumen")
@login_required
def pdf_resumen_route():
    tri =request.args.get("trimestre","T1")
    anio=int(request.args.get("anio",datetime.date.today().year))
    buf=generar_pdf_resumen(tri,anio)
    nombre=f"Resumen_{tri}_{anio}.pdf"
    return send_file(buf,mimetype="application/pdf",as_attachment=True,download_name=nombre)

@app.route("/api/pdf_listado")
@login_required
def pdf_listado_route():
    dpto = request.args.get("departamento","")
    tri  = request.args.get("trimestre","")
    anio = request.args.get("anio","")
    busq = request.args.get("buscar","")
    con  = get_db()
    q    = "SELECT * FROM reportes WHERE 1=1"
    p    = []
    if dpto: q+=" AND departamento=?"; p.append(dpto)
    if tri:  q+=" AND trimestre=?";    p.append(tri)
    if anio: q+=" AND anio=?";         p.append(int(anio))
    if busq: q+=" AND (numero LIKE ? OR departamento LIKE ? OR modelo LIKE ? OR serial LIKE ?)"; p+=[f"%{busq}%"]*4
    q+=" ORDER BY fecha_registro DESC"
    rows=[dict(r) for r in con.execute(q,p)]
    con.close()
    filtros={"departamento":dpto,"trimestre":tri,"anio":anio,"buscar":busq}
    buf=generar_pdf_listado(rows,filtros)
    nombre=f"Listado_Reportes_{datetime.date.today().strftime('%d%m%Y')}.pdf"
    return send_file(buf,mimetype="application/pdf",as_attachment=True,download_name=nombre)

@app.route("/api/siguiente_numero")
@login_required
def siguiente_numero():
    con=get_db()
    anio=datetime.date.today().year
    rows=con.execute("SELECT numero FROM reportes WHERE anio=?",(anio,)).fetchall()
    nums=[]
    for row in rows:
        try:
            n=int(str(row[0]).split('/')[0].replace('RRE-','').strip())
            nums.append(n)
        except: pass
    siguiente=(max(nums)+1) if nums else 1
    con.close()
    return jsonify({"numero":f"RRE-{siguiente:02d}/{str(anio)[2:]}"})

def get_logo_img(path, w, h):
    from reportlab.platypus import Image as RLImg
    if path.exists():
        return RLImg(str(path), w, h)
    return ""

def generar_pdf(r):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import json as _json

    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf, pagesize=letter,
                          leftMargin=1.5*cm, rightMargin=1.5*cm,
                          topMargin=1.2*cm, bottomMargin=1.2*cm)
    W,H=letter; ancho=W-3*cm
    negro=colors.black
    azul_titulo=colors.HexColor("#3D1A00")
    azul_sub=colors.HexColor("#1a4a8a")
    gris_borde=colors.HexColor("#888888")

    def es(n,**kw):
        b={"fontName":"Helvetica","fontSize":9,"leading":11,"textColor":negro}
        b.update(kw); return ParagraphStyle(n,**b)

    story=[]

    logo_alc  = get_logo_img(LOGO_ALCALDIA, 2.8*cm, 2.8*cm)
    logo_info = get_logo_img(LOGO_INFO, 2.0*cm, 2.0*cm)

    num_box = Table([[Paragraph(f"<b>N°.</b>",es("nb",fontSize=9)),
                      Paragraph(f"<b>{r.get('numero','')}</b>",es("nv",fontSize=11,textColor=azul_sub))]],
                    colWidths=[1.1*cm, 3*cm])
    num_box.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),1.5,negro),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),5),
    ]))

    hdr=Table([[
        logo_alc,
        [Paragraph("<b>Recepción de Equipos</b>",
                   es("t1",fontSize=24,alignment=TA_CENTER,leading=30,fontName="Helvetica-Bold",textColor=azul_titulo)),
         Paragraph("Coordinación de Informática",
                   es("t2",fontSize=12,textColor=azul_sub,alignment=TA_CENTER,leading=16))],
        [logo_info, Spacer(1,0.2*cm), num_box]
    ]], colWidths=[3*cm, ancho-7*cm, 4*cm])
    hdr.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BOX",(0,0),(-1,-1),2,negro),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(1,0),(1,0),8),("RIGHTPADDING",(1,0),(1,0),8),
        ("ALIGN",(2,0),(2,0),"CENTER"),
    ]))
    story+=[hdr, Spacer(1,0.3*cm)]

    border_st = TableStyle([
        ("BOX",(0,0),(-1,-1),1,negro),
        ("INNERGRID",(0,0),(-1,-1),0.5,gris_borde),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),5),
    ])

    def campo(lbl, val, w_lbl=3*cm, w_val=None, bold_lbl=True):
        wv = w_val or (ancho - w_lbl)
        fn = "Helvetica-Bold" if bold_lbl else "Helvetica"
        t=Table([[Paragraph(f"<b>{lbl}</b>",es("cl",fontName=fn,fontSize=10)),
                  Paragraph(str(val or ""),es("cv",fontSize=10,textColor=azul_sub))]],
                colWidths=[w_lbl, wv])
        t.setStyle(border_st)
        return t

    def campo2(l1,v1,l2,v2, w1=3*cm, w2=3*cm):
        mitad=ancho/2
        t=Table([[Paragraph(f"<b>{l1}</b>",es("l1",fontName="Helvetica-Bold",fontSize=10)),
                  Paragraph(str(v1 or ""),es("v1",fontSize=10,textColor=azul_sub)),
                  Paragraph(f"<b>{l2}</b>",es("l2",fontName="Helvetica-Bold",fontSize=10)),
                  Paragraph(str(v2 or ""),es("v2",fontSize=10,textColor=azul_sub))]],
                colWidths=[w1,mitad-w1,w2,mitad-w2])
        t.setStyle(border_st)
        return t

    story.append(campo2("Departamento:",r.get("departamento",""),"Fecha:",r.get("fecha",""),3.2*cm,1.5*cm))
    story.append(Spacer(1,0.05*cm))
    story.append(campo("código de bienes municipales:", r.get("codigo_bienes",""), 4.8*cm))
    story.append(Spacer(1,0.05*cm))
    story.append(campo2("Equipo:",r.get("equipo",""),"Marca:",r.get("marca",""),2*cm,1.8*cm))
    story.append(Spacer(1,0.05*cm))
    story.append(campo2("Modelo:",r.get("modelo",""),"Serial:",r.get("serial",""),2*cm,1.8*cm))
    story.append(Spacer(1,0.3*cm))

    titulo_chk=Table([[Paragraph("<b>Chequeo Previo</b>",
                                  es("ch",fontSize=13,alignment=TA_CENTER,fontName="Helvetica-Bold"))]],
                     colWidths=[ancho])
    titulo_chk.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,negro),
                                     ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(titulo_chk)

    comp_items=["Antena Wifi","DVD","Ram","Disco duro","Cable de Poder","Tarjeta de red","Drivers","Otros"]
    lap_items =["Maletín","Batería","Cable de Poder","Drivers","Otros"]
    imp_items =["C. de comunicación","Tapas","Cartuchos","Cable de Poder","Drivers","Otros"]
    comp_marc=_json.loads(r.get("chequeo_computador","[]"))
    lap_marc =_json.loads(r.get("chequeo_laptop","[]"))
    imp_marc =_json.loads(r.get("chequeo_impresora","[]"))

    def lista_chk(titulo, items, marcados):
        rows=[[Paragraph(f"<b>☐ {titulo}</b>",es("ct",fontSize=9,fontName="Helvetica-Bold",alignment=TA_CENTER))]]
        for it in items:
            mark="✓" if any(it in m for m in (marcados or [])) else "☐"
            rows.append([Paragraph(f"{mark} {it}",es(f"i{it}",fontSize=8,leading=13))])
        t=Table(rows,colWidths=[ancho/3-0.1*cm])
        t.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,negro),
                                ("LINEBELOW",(0,0),(-1,0),1,negro),
                                ("TOPPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),6)]))
        return t

    chk_row=Table([[lista_chk("Computador",comp_items,comp_marc),
                    lista_chk("Laptop",lap_items,lap_marc),
                    lista_chk("Impresora",imp_items,imp_marc)]],
                  colWidths=[ancho/3]*3)
    chk_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                                  ("BOX",(0,0),(-1,-1),1,negro),
                                  ("INNERGRID",(0,0),(-1,-1),1,negro)]))
    story+=[chk_row, Spacer(1,0.3*cm)]

    titulo_tr=Table([[Paragraph("<b>Trabajos Realizados</b>",
                                 es("tr",fontSize=13,alignment=TA_CENTER,fontName="Helvetica-Bold"))]],
                    colWidths=[ancho])
    titulo_tr.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,negro),
                                    ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(titulo_tr)

    trab_todos=["Chequeo de Equipo","Formateo de disco duro","Respaldo de Data",
                "Instalación de sistema operativo","Instalación de office",
                "Instalación de impresora","Instalación de impresora en red",
                "Instalación de anti virus y actualización","Restauración de la data"]
    trab_marc=_json.loads(r.get("trabajos","[]"))
    c1=trab_todos[:5]; c2=trab_todos[5:]

    def col_t(items):
        rows=[]
        for it in items:
            mark="✓" if any(it in m for m in trab_marc) else "☐"
            rows.append([Paragraph(f"{mark} {it}",es(f"tr{it}",fontSize=8,leading=14))])
        return rows

    trb=Table([[col_t(c1), col_t(c2)]],colWidths=[ancho/2]*2)
    trb.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,negro),
                              ("INNERGRID",(0,0),(-1,-1),0.5,negro),
                              ("VALIGN",(0,0),(-1,-1),"TOP"),
                              ("TOPPADDING",(0,0),(-1,-1),4),
                              ("LEFTPADDING",(0,0),(-1,-1),8)]))
    story.append(trb)

    story.append(Spacer(1,0.1*cm))
    otros_t=Table([[Paragraph("<b>Otros:</b>",es("ol",fontSize=9,fontName="Helvetica-Bold")),
                    Paragraph(str(r.get("otros","") or ""),es("ov",fontSize=9,textColor=azul_sub))]],
                  colWidths=[1.5*cm,ancho-1.5*cm])
    otros_t.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,negro),
                                  ("MINROWHEIGHT",(0,0),(0,0),1.4*cm),
                                  ("VALIGN",(0,0),(-1,-1),"TOP"),
                                  ("TOPPADDING",(0,0),(-1,-1),5),
                                  ("LEFTPADDING",(0,0),(-1,-1),5)]))
    story.append(otros_t)
    story.append(Spacer(1,0.3*cm))

    foto_box=Table([[Paragraph("",es("fb"))]],colWidths=[ancho])
    foto_box.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,negro),
                                   ("MINROWHEIGHT",(0,0),(0,0),2.5*cm)]))
    story.append(foto_box)
    story.append(Spacer(1,0.3*cm))

    firmas=Table([[
        [Paragraph("________________________",es("f1",fontSize=8,alignment=TA_CENTER)),
         Paragraph("Recibe Conforme",es("fl1",fontSize=9,alignment=TA_CENTER,fontName="Helvetica-Bold")),
         Paragraph(str(r.get("nombre_usuario","")),es("fn",fontSize=9,alignment=TA_CENTER,textColor=azul_sub)),
         Paragraph(str(r.get("cedula_usuario","")),es("fci",fontSize=8,alignment=TA_CENTER,textColor=azul_sub))],
        [Paragraph("________________________",es("f2",fontSize=8,alignment=TA_CENTER)),
         Paragraph("Soporte Técnico",es("fl2",fontSize=9,alignment=TA_CENTER,fontName="Helvetica-Bold")),
         Paragraph(str(r.get("tecnico","")),es("ft",fontSize=9,alignment=TA_CENTER,textColor=azul_sub))]
    ]],colWidths=[ancho/2]*2)
    firmas.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                                 ("TOPPADDING",(0,0),(-1,-1),10),
                                 ("ALIGN",(0,0),(-1,-1),"CENTER")]))
    story.append(firmas)
    story.append(Spacer(1,0.2*cm))
    story.append(Paragraph(
        'Dirección: A.v Miranda Palacio Municipal "Alcaldía Bolivariana del Municipio Carlos Arvelo"',
        es("pie",fontSize=8,textColor=colors.grey,alignment=TA_CENTER)))
    story.append(Paragraph(
        "Telf. Fax: 0245-3412069  |  04144153893  |  04262410794",
        es("pie2",fontSize=7.5,textColor=colors.grey,alignment=TA_CENTER)))

    doc.build(story)
    buf.seek(0)
    return buf

def generar_pdf_resumen(tri, anio):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    con=get_db(); p=(tri,anio)
    total =con.execute("SELECT COUNT(*) FROM reportes WHERE trimestre=? AND anio=?",p).fetchone()[0]
    dptos =[(r[0],r[1]) for r in con.execute("SELECT departamento,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY departamento ORDER BY COUNT(*) DESC",p)]
    equipos=[(r[0],r[1]) for r in con.execute("SELECT equipo,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY equipo ORDER BY COUNT(*) DESC",p)]
    modelos=[(r[0]+' '+r[1],r[2]) for r in con.execute("SELECT marca,modelo,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY marca,modelo ORDER BY COUNT(*) DESC",p)]
    estados=[(r[0],r[1]) for r in con.execute("SELECT estado,COUNT(*) FROM reportes WHERE trimestre=? AND anio=? GROUP BY estado ORDER BY COUNT(*) DESC",p)]
    con.close()

    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=1.8*cm,rightMargin=1.8*cm,topMargin=1.5*cm,bottomMargin=1.8*cm)
    W,H=A4; ancho=W-3.6*cm
    azul=colors.HexColor("#003B6F"); dorado=colors.HexColor("#C8961E")
    gris=colors.HexColor("#EEF2F7")

    def es(n,**kw):
        b={"fontName":"Helvetica","fontSize":9,"leading":12,"textColor":colors.black}
        b.update(kw); return ParagraphStyle(n,**b)

    story=[]
    logo_alc  = get_logo_img(LOGO_ALCALDIA, 2*cm, 2*cm)
    logo_info = get_logo_img(LOGO_INFO, 1.6*cm, 1.6*cm)

    ht=Table([[logo_alc,[
        Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA · ESTADO CARABOBO",es("h1",fontSize=7,textColor=colors.grey,alignment=TA_CENTER)),
        Paragraph("ALCALDÍA DE CARLOS ARVELO",es("h2",fontName="Helvetica-Bold",fontSize=13,textColor=azul,alignment=TA_CENTER)),
        Paragraph("COORDINACIÓN DE INFORMÁTICA",es("h3",fontName="Helvetica-Bold",fontSize=9,textColor=azul,alignment=TA_CENTER)),
        Paragraph(f"RESUMEN TRIMESTRAL — {tri} {anio}",es("h4",fontName="Helvetica-Bold",fontSize=11,textColor=dorado,alignment=TA_CENTER)),
    ],logo_info]],colWidths=[2.2*cm,ancho-4.4*cm,2.2*cm])
    ht.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,0),2,dorado),("BOTTOMPADDING",(0,0),(-1,0),8)]))
    story+=[ht,Spacer(1,.4*cm)]

    tot=Table([[Paragraph(f"Total de reportes — {tri} {anio}:",es("tt",fontName="Helvetica-Bold",fontSize=11,textColor=azul)),
                Paragraph(str(total),es("tn",fontName="Helvetica-Bold",fontSize=22,textColor=dorado))]],
              colWidths=[ancho-2*cm,2*cm])
    tot.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(1,0),"CENTER"),
                             ("BOX",(0,0),(-1,-1),1,dorado),("TOPPADDING",(0,0),(-1,-1),8),
                             ("BOTTOMPADDING",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),10)]))
    story+=[tot,Spacer(1,.3*cm)]

    def tabla_res(titulo,datos):
        barra=Table([[Paragraph("  "+titulo,es("s",fontName="Helvetica-Bold",fontSize=9,textColor=colors.white))]],colWidths=[ancho])
        barra.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),azul),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        story.append(barra)
        filas=[[Paragraph("<b>Descripción</b>",es("eh",textColor=azul)),Paragraph("<b>Cant.</b>",es("ec",textColor=azul)),Paragraph("<b>%</b>",es("ep",textColor=azul))]]
        for i,(d,c) in enumerate(datos):
            pct=f"{round(c/total*100)}%" if total else "0%"
            filas.append([Paragraph(str(d),es(f"d{i}")),Paragraph(str(c),es(f"c{i}")),Paragraph(pct,es(f"p{i}"))])
        t=Table(filas,colWidths=[ancho-4*cm,2*cm,2*cm])
        t.setStyle(TableStyle([("BOX",(0,0),(-1,-1),.5,colors.HexColor("#CBD5E1")),("INNERGRID",(0,0),(-1,-1),.5,colors.HexColor("#CBD5E1")),
                               ("BACKGROUND",(0,0),(-1,0),gris),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),5)]))
        story+=[t,Spacer(1,.3*cm)]

    tabla_res("REPORTES POR DEPARTAMENTO",dptos)
    tabla_res("REPORTES POR TIPO DE EQUIPO",equipos)
    tabla_res("REPORTES POR MARCA / MODELO",modelos)
    tabla_res("REPORTES POR ESTADO",estados)
    story.append(Paragraph(f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} — Coordinación de Informática · Alcaldía Carlos Arvelo",
                           es("pie",fontSize=7,textColor=colors.grey,alignment=TA_CENTER)))
    doc.build(story)
    buf.seek(0)
    return buf

def generar_pdf_listado(rows, filtros=None):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    import json as _json

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    W, H = landscape(A4); ancho = W - 3*cm
    azul=colors.HexColor("#003B6F"); azul2=colors.HexColor("#0055A5")
    dorado=colors.HexColor("#C8961E"); grisF=colors.HexColor("#F8FAFF")
    ESTADO_COL={"Recibido":colors.HexColor("#DBEAFE"),"En Diagnóstico":colors.HexColor("#FEF3C7"),
                "En Reparación":colors.HexColor("#FFEDD5"),"Listo":colors.HexColor("#DCFCE7"),"Entregado":colors.HexColor("#F1F5F9")}

    def es(n,**kw):
        b={"fontName":"Helvetica","fontSize":8,"leading":10,"textColor":colors.black}
        b.update(kw); return ParagraphStyle(n,**b)

    story=[]
    logo_alc  = get_logo_img(LOGO_ALCALDIA, 1.8*cm, 1.8*cm)
    logo_info = get_logo_img(LOGO_INFO, 1.4*cm, 1.4*cm)

    hdr=Table([[logo_alc,[
        Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA · ESTADO CARABOBO",es("h0",fontSize=7,textColor=colors.grey,alignment=TA_CENTER)),
        Paragraph("ALCALDÍA BOLIVARIANA DEL MUNICIPIO CARLOS ARVELO",es("h1",fontName="Helvetica-Bold",fontSize=13,textColor=azul,alignment=TA_CENTER)),
        Paragraph("COORDINACIÓN DE INFORMÁTICA",es("h2",fontName="Helvetica-Bold",fontSize=9,textColor=azul2,alignment=TA_CENTER)),
        Paragraph("LISTADO DE REPORTES DE RECEPCIÓN DE EQUIPOS",es("h3",fontName="Helvetica-Bold",fontSize=10,textColor=dorado,alignment=TA_CENTER)),
    ],[logo_info, Paragraph(f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}",es("hf",fontSize=8,alignment=TA_RIGHT,textColor=colors.grey))]]],
    colWidths=[2*cm, ancho-4.5*cm, 2.5*cm])
    hdr.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,0),2,dorado),("BOTTOMPADDING",(0,0),(-1,0),8)]))
    story+=[hdr,Spacer(1,0.25*cm)]

    if filtros:
        partes=[]
        if filtros.get("departamento"): partes.append(f"Departamento: {filtros['departamento']}")
        if filtros.get("trimestre"):    partes.append(f"Trimestre: {filtros['trimestre']}")
        if filtros.get("anio"):         partes.append(f"Año: {filtros['anio']}")
        if filtros.get("buscar"):       partes.append(f'Búsqueda: "{filtros["buscar"]}"')
        if partes:
            story.append(Table([[Paragraph("Filtros: "+"  •  ".join(partes),es("ft",fontSize=8,textColor=azul2))]],
                               colWidths=[ancho],style=[("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#EEF2F7")),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),8)]))
            story.append(Spacer(1,0.15*cm))

    story.append(Table([[Paragraph(f"Total de registros: <b>{len(rows)}</b>",es("tot",fontSize=9,textColor=azul))]],
                       colWidths=[ancho],style=[("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),6)]))
    story.append(Spacer(1,0.15*cm))

    enc=[Paragraph("<b>N°</b>",es("e0",textColor=colors.white,alignment=TA_CENTER)),
         Paragraph("<b>Fecha</b>",es("e1",textColor=colors.white,alignment=TA_CENTER)),
         Paragraph("<b>Departamento</b>",es("e2",textColor=colors.white)),
         Paragraph("<b>Equipo</b>",es("e3",textColor=colors.white)),
         Paragraph("<b>Marca / Modelo</b>",es("e4",textColor=colors.white)),
         Paragraph("<b>Serial</b>",es("e5",textColor=colors.white,alignment=TA_CENTER)),
         Paragraph("<b>Trabajos Realizados</b>",es("e7",textColor=colors.white)),
         Paragraph("<b>Estado</b>",es("e8",textColor=colors.white,alignment=TA_CENTER))]
    cw=[2*cm,1.6*cm,3.5*cm,2.4*cm,3.5*cm,2.4*cm,7*cm,2.4*cm]
    data=[enc]
    ts=[("BACKGROUND",(0,0),(-1,0),azul),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),8),
        ("TOPPADDING",(0,0),(-1,0),6),("BOTTOMPADDING",(0,0),(-1,0),6),
        ("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#CBD5E1")),
        ("INNERGRID",(0,0),(-1,-1),0.3,colors.HexColor("#CBD5E1")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,1),(-1,-1),4),("BOTTOMPADDING",(0,1),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),4)]

    for i,row in enumerate(rows):
        trab=_json.loads(row.get("trabajos","[]"))
        trab_txt=" / ".join(trab) if trab else "—"
        estado=row.get("estado","—")
        fila=[Paragraph(str(row.get("numero","")),es(f"r{i}0",fontName="Helvetica-Bold",alignment=TA_CENTER)),
              Paragraph(str(row.get("fecha","")),es(f"r{i}1",alignment=TA_CENTER)),
              Paragraph(str(row.get("departamento","")),es(f"r{i}2")),
              Paragraph(str(row.get("equipo","")),es(f"r{i}3")),
              Paragraph(f"{row.get('marca','')} {row.get('modelo','')}".strip(),es(f"r{i}4",fontName="Helvetica-Bold")),
              Paragraph(str(row.get("serial","")),es(f"r{i}5",alignment=TA_CENTER,fontSize=7)),
              Paragraph(trab_txt,es(f"r{i}7",fontSize=7,leading=9)),
              Paragraph(estado,es(f"r{i}8",alignment=TA_CENTER,fontName="Helvetica-Bold",fontSize=7))]
        data.append(fila)
        ri=i+1
        bg=grisF if i%2==0 else colors.white
        ts.append(("BACKGROUND",(0,ri),(-2,ri),bg))
        ts.append(("BACKGROUND",(7,ri),(7,ri),ESTADO_COL.get(estado,colors.white)))

    tabla=Table(data,colWidths=cw,repeatRows=1)
    tabla.setStyle(TableStyle(ts))
    story.append(tabla)
    story.append(Spacer(1,0.3*cm))
    story.append(Paragraph(
        f"Coordinación de Informática · Alcaldía Bolivariana del Municipio Carlos Arvelo · "
        f"Estado Carabobo · Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        es("pie",fontSize=7,textColor=colors.grey,alignment=TA_CENTER)))
    doc.build(story)
    buf.seek(0)
    return buf

def generar_pdf_servicio_blank():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,
                          leftMargin=1*cm,rightMargin=1*cm,
                          topMargin=1*cm,bottomMargin=1*cm)
    W,H=A4; ancho=W-2*cm
    negro=colors.black; azul=colors.HexColor("#003B6F")
    dorado=colors.HexColor("#C8961E")

    def es(n,**kw):
        b={"fontName":"Helvetica","fontSize":8,"leading":10,"textColor":negro}
        b.update(kw); return ParagraphStyle(n,**b)

    def mini_reporte():
        logo_alc  = get_logo_img(LOGO_ALCALDIA, 1.2*cm, 1.2*cm)
        logo_info = get_logo_img(LOGO_INFO, 1*cm, 1*cm)
        cab=Table([[
            logo_alc,
            [Paragraph("Reporte de Servicio Técnico",es("rt",fontSize=11,fontName="Helvetica-Bold",alignment=TA_CENTER,textColor=azul,leading=14)),
             Paragraph("Coordinación de Informática",es("ci",fontSize=7,textColor=dorado,alignment=TA_CENTER))],
            [logo_info, Paragraph("N°._______",es("nn",fontSize=9,fontName="Helvetica-Bold",alignment=TA_LEFT))]
        ]],colWidths=[1.4*cm, ancho-3.2*cm, 1.8*cm])
        cab.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,0),1.5,negro),
                                  ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        line=colors.HexColor("#AAAAAA")
        def dos_lineas(l1,l2,aw1=2.5*cm,aw2=2.5*cm):
            mitad=ancho/2
            t=Table([[Paragraph(f"<b>{l1}</b>",es("l1",fontSize=8)),Paragraph("",es("v1")),
                      Paragraph(f"<b>{l2}</b>",es("l2",fontSize=8)),Paragraph("",es("v2"))]],
                    colWidths=[aw1,mitad-aw1,aw2,mitad-aw2])
            t.setStyle(TableStyle([("LINEBELOW",(1,0),(1,0),0.8,line),("LINEBELOW",(3,0),(3,0),0.8,line),
                                    ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),2)]))
            return t
        det=Table([[Paragraph("<b>Fallas:</b>",es("dt",fontSize=8)),Paragraph("",es("dv"))]],
                  colWidths=[1.5*cm,ancho-1.5*cm])
        det.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,line),("MINROWHEIGHT",(0,0),(0,0),1.4*cm),
                                  ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),3)]))
        trab=Table([[Paragraph("<b>Trabajos Realizados:</b>",es("tw",fontSize=8)),Paragraph("",es("twv"))]],
                   colWidths=[3.5*cm,ancho-3.5*cm])
        trab.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,line),("MINROWHEIGHT",(0,0),(0,0),1.4*cm),
                                   ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),3)]))
        firma=Table([[Paragraph("_______________________",es("f1",fontSize=7,alignment=TA_CENTER)),
                      Paragraph("_______________________",es("f2",fontSize=7,alignment=TA_CENTER))]],colWidths=[ancho/2]*2)
        firma.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),8),("ALIGN",(0,0),(-1,-1),"CENTER")]))
        firma2=Table([[Paragraph("Recibe Conforme",es("fl1",fontSize=7,alignment=TA_CENTER,textColor=colors.grey)),
                       Paragraph("Soporte Técnico",es("fl2",fontSize=7,alignment=TA_CENTER,textColor=colors.grey))]],colWidths=[ancho/2]*2)
        firma2.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),("ALIGN",(0,0),(-1,-1),"CENTER")]))
        pie=Table([[Paragraph('Dirección: A.v Miranda Palacio Municipal "Alcaldía Bolivariana del Municipio Carlos Arvelo"',
                               es("pie",fontSize=7,alignment=TA_CENTER,textColor=colors.grey))]],colWidths=[ancho])

        inner=[cab,Spacer(1,0.1*cm),dos_lineas("Departamento:","Fecha:",3*cm,1.5*cm),
               dos_lineas("Equipo:","Marca:",2*cm,1.5*cm),dos_lineas("Modelo:","Serial:",2*cm,1.5*cm),
               Spacer(1,0.1*cm),det,Spacer(1,0.05*cm),trab,Spacer(1,0.1*cm),firma,firma2,pie]
        wrapper=Table([[inner]],colWidths=[ancho])
        wrapper.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1.5,negro),
                                      ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                                      ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]))
        return wrapper

    story=[]
    for i in range(3):
        story.append(mini_reporte())
        if i < 2:
            story.append(Spacer(1,0.3*cm))
            story.append(Table([[Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
                                           es("sep",fontSize=7,textColor=colors.grey,alignment=TA_CENTER))]],colWidths=[ancho]))
            story.append(Spacer(1,0.3*cm))
    doc.build(story)
    buf.seek(0)
    return buf

if __name__ == "__main__":
    init_db()
    con = get_db()
    existe = con.execute("SELECT id FROM usuarios WHERE cedula = '12345678'").fetchone()
    if not existe:
        crear_usuario('12345678', 'Root', 'Superadmin', 'Admin@2026', 'superadmin')
        print("Usuario superadmin creado: cédula 12345678 / contraseña Admin@2026")
    con.close()
    import shutil
    for src, dst in [
        (BASE_DIR/"logo_alcaldia.jpeg", LOGO_ALCALDIA),
        (BASE_DIR/"logo_informatica.jpeg", LOGO_INFO),
    ]:
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
    print("="*55)
    print("  Alcaldía Carlos Arvelo - Sistema de Reportes v5.0 (roles usuarios/superadmin/admin)")
    print("  Abrir en: http://localhost:5000")
    print("="*55)
    app.run(debug=False, port=5000, host='0.0.0.0')
