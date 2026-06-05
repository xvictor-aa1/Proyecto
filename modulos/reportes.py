from flask import Blueprint, request, jsonify, session, abort, send_file
from database import get_db
from modulos.auth import login_required
from modulos.audit import log_event
import datetime, json
from pdf.generator import generar_pdf, generar_pdf_resumen, generar_pdf_listado
import mysql.connector

# Modulo principal del Sistema de Reportee
reportes_bp = Blueprint('reportes', __name__)

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

def _ip():
    return request.remote_addr or ""

@reportes_bp.route("/departamentos")
def get_departamentos():
    return jsonify(DEPARTAMENTOS)

@reportes_bp.route("/tecnicos")
def get_tecnicos():
    return jsonify(TECNICOS)

@reportes_bp.route("/reportes", methods=["GET"])
@login_required
def listar():
    dpto = request.args.get("departamento","")
    tri  = request.args.get("trimestre","")
    busq = request.args.get("buscar","")
    anio = request.args.get("anio","")
    db  = get_db()
    q    = "SELECT * FROM reportes WHERE 1=1"
    p    = []
    if dpto: q+=" AND departamento=?"; p.append(dpto)
    if tri:  q+=" AND trimestre=?";    p.append(tri)
    if anio: q+=" AND anio=?";         p.append(int(anio))
    if busq: q+=" AND (numero LIKE ? OR departamento LIKE ? OR modelo LIKE ? OR serial LIKE ?)"; p+=[f"%{busq}%"]*4
    q+=" ORDER BY fecha_registro DESC"
    rows = db.execute(q, p).fetchall()
    db.close()
    log_event(session.get("nombre_usuario"), "Consulta listado de reportes",
              f"Filtros: departamento={dpto}, trimestre={tri}, anio={anio}, búsqueda={busq}",
              ip=_ip())
    return jsonify(rows)

@reportes_bp.route("/reportes/<int:rid>", methods=["GET"])
@login_required
def obtener(rid):
    db=get_db()
    r=db.execute("SELECT * FROM reportes WHERE id=?",(rid,)).fetchone()
    db.close()
    if not r: abort(404)
    log_event(session.get("nombre_usuario"), "Consulta reporte individual", f"ID {rid}", ip=_ip())
    return jsonify(r)

@reportes_bp.route("/reportes", methods=["POST"])
@login_required
def crear():
    d=request.json
    if not d.get("numero"):
        return jsonify({"error":"El número de reporte es obligatorio"}),400
    hoy=datetime.date.today()
    mes=hoy.month
    tri="T1" if mes<=3 else "T2" if mes<=6 else "T3" if mes<=9 else "T4"
    db=get_db()
    try:
        db.execute("""
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
        db.commit()
        nid = db.execute("SELECT LAST_INSERT_ID() AS id").fetchone()["id"]
        log_event(session.get("nombre_usuario"), "Creación de reporte",
                  f"N° {d['numero']}, dpto {d.get('departamento','')}, equipo {d.get('equipo','')}",
                  ip=_ip())
        db.close()
        return jsonify({"ok":True,"id":nid})
    except mysql.connector.IntegrityError:
        db.close()
        return jsonify({"error":f"El N° {d['numero']} ya existe"}),409

@reportes_bp.route("/reportes/<int:rid>", methods=["PUT"])
@login_required
def actualizar(rid):
    d=request.json
    hoy=datetime.date.today()
    mes=hoy.month
    tri="T1" if mes<=3 else "T2" if mes<=6 else "T3" if mes<=9 else "T4"
    db=get_db()
    db.execute("""
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
    db.commit()
    log_event(session.get("nombre_usuario"), "Actualización de reporte",
              f"ID {rid}, número {d.get('numero','')}", ip=_ip())
    db.close()
    return jsonify({"ok":True})

@reportes_bp.route("/reportes/<int:rid>", methods=["DELETE"])
@login_required
def eliminar(rid):
    if session.get("rol_usuario") != "superadmin":
        return jsonify({"error":"Solo el administrador puede eliminar reportes"}),403
    db=get_db()
    db.execute("DELETE FROM reportes WHERE id=?",(rid,))
    db.commit()
    log_event(session.get("nombre_usuario"), "Eliminación de reporte",
              f"ID {rid} eliminado", ip=_ip())
    db.close()
    return jsonify({"ok":True})

@reportes_bp.route("/resumen")
@login_required
def resumen():
    tri =request.args.get("trimestre","T1")
    anio=int(request.args.get("anio",datetime.date.today().year))
    db=get_db()
    total =db.execute("SELECT COUNT(*) as cnt FROM reportes WHERE trimestre=? AND anio=?", (tri,anio)).fetchone()["cnt"]
    dptos = [(r["departamento"], r["cnt"]) for r in db.execute("SELECT departamento, COUNT(*) as cnt FROM reportes WHERE trimestre=? AND anio=? GROUP BY departamento ORDER BY cnt DESC", (tri,anio)).fetchall()]
    equipos = [(r["equipo"], r["cnt"]) for r in db.execute("SELECT equipo, COUNT(*) as cnt FROM reportes WHERE trimestre=? AND anio=? GROUP BY equipo ORDER BY cnt DESC", (tri,anio)).fetchall()]
    modelos = [(r["marca"] + ' ' + r["modelo"], r["cnt"]) for r in db.execute("SELECT marca, modelo, COUNT(*) as cnt FROM reportes WHERE trimestre=? AND anio=? GROUP BY marca, modelo ORDER BY cnt DESC", (tri,anio)).fetchall()]
    estados = [(r["estado"], r["cnt"]) for r in db.execute("SELECT estado, COUNT(*) as cnt FROM reportes WHERE trimestre=? AND anio=? GROUP BY estado ORDER BY cnt DESC", (tri,anio)).fetchall()]
    db.close()
    log_event(session.get("nombre_usuario"), "Consulta resumen", f"Trimestre {tri} año {anio}", ip=_ip())
    return jsonify({"total":total,"dptos":dptos,"equipos":equipos,"modelos":modelos,"estados":estados})

@reportes_bp.route("/siguiente_numero")
@login_required
def siguiente_numero():
    db=get_db()
    anio=datetime.date.today().year
    rows=db.execute("SELECT numero FROM reportes WHERE anio=?",(anio,)).fetchall()
    nums=[]
    for row in rows:
        try:
            n=int(str(row["numero"]).split('/')[0].replace('RRE-','').strip())
            nums.append(n)
        except: pass
    db.close()
    siguiente=(max(nums)+1) if nums else 1
    log_event(session.get("nombre_usuario"), "Solicitar siguiente número", f"{siguiente}", ip=_ip())
    return jsonify({"numero":f"RRE-{siguiente:02d}/{str(anio)[2:]}"})

@reportes_bp.route("/pdf/<int:rid>")
@login_required
def pdf_reporte(rid):
    db=get_db()
    row=db.execute("SELECT * FROM reportes WHERE id=?",(rid,)).fetchone()
    db.close()
    if not row: abort(404)

    reporte_numero = row['numero']
    equipo = row.get('equipo','')
    marca = row.get('marca','')
    modelo = row.get('modelo','')
    estado = row.get('estado','')
    departamento = row.get('departamento','')

    chequeo_total = 0
    for campo in ['chequeo_computador','chequeo_laptop','chequeo_impresora']:
        chequeo_total += len(json.loads(row.get(campo, '[]')))
    trabajos_total = len(json.loads(row.get('trabajos', '[]')))

    buf=generar_pdf(row)

    log_event(
        session.get("nombre_usuario"),
        "Generación de PDF de reporte individual",
        (
            f"Reporte N° {reporte_numero} | "
            f"Equipo: {equipo} | Marca: {marca} {modelo} | "
            f"Estado: {estado} | Departamento: {departamento} | "
            f"Chequeos marcados: {chequeo_total} | Trabajos realizados: {trabajos_total}"
        ),
        ip=_ip()
    )

    nombre=f"Recepcion_{reporte_numero.replace('/','_')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)

@reportes_bp.route("/pdf_resumen")
@login_required
def pdf_resumen_route():
    tri =request.args.get("trimestre","T1")
    anio=int(request.args.get("anio",datetime.date.today().year))
    buf=generar_pdf_resumen(tri,anio)
    log_event(session.get("nombre_usuario"), "Generación PDF resumen",
              f"Trimestre {tri} año {anio}", ip=_ip())
    nombre=f"Resumen_{tri}_{anio}.pdf"
    return send_file(buf,mimetype="application/pdf",as_attachment=True,download_name=nombre)

@reportes_bp.route("/pdf_listado")
@login_required
def pdf_listado_route():
    dpto = request.args.get("departamento","")
    tri  = request.args.get("trimestre","")
    anio = request.args.get("anio","")
    busq = request.args.get("buscar","")
    db  = get_db()
    q    = "SELECT * FROM reportes WHERE 1=1"
    p    = []
    if dpto: q+=" AND departamento=?"; p.append(dpto)
    if tri:  q+=" AND trimestre=?";    p.append(tri)
    if anio: q+=" AND anio=?";         p.append(int(anio))
    if busq: q+=" AND (numero LIKE ? OR departamento LIKE ? OR modelo LIKE ? OR serial LIKE ?)"; p+=[f"%{busq}%"]*4
    q+=" ORDER BY fecha_registro DESC"
    rows = db.execute(q, p).fetchall()
    db.close()
    filtros={"departamento":dpto,"trimestre":tri,"anio":anio,"buscar":busq}
    buf=generar_pdf_listado(rows, filtros)
    log_event(session.get("nombre_usuario"), "Generación PDF listado",
              f"Cantidad: {len(rows)}, filtros: {filtros}", ip=_ip())
    nombre=f"Listado_Reportes_{datetime.date.today().strftime('%d%m%Y')}.pdf"
    return send_file(buf,mimetype="application/pdf",as_attachment=True,download_name=nombre)
