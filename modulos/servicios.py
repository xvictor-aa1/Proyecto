from flask import Blueprint, request, jsonify, send_file
from database import get_db
from modulos.auth import login_required
from modulos.audit import log_event
import datetime
from pdf.generator import generar_pdf_servicio_blank

# Modulo de servicio del Sistema de Reporte
servicios_bp = Blueprint('servicios', __name__)

def _ip():
    return request.remote_addr or ""

@servicios_bp.route("/reporte_servicio", methods=["GET"])
@login_required
def listar_servicio():
    db=get_db()
    rows=db.execute("SELECT * FROM reportes_servicio ORDER BY fecha_registro DESC").fetchall()
    db.close()
    log_event(session.get("nombre_usuario"), "Consulta listado de servicios",
              f"Se obtuvieron {len(rows)} registros", ip=_ip())
    return jsonify(rows)

@servicios_bp.route("/reporte_servicio", methods=["POST"])
@login_required
def crear_servicio():
    d=request.json
    if not d.get("numero"):
        return jsonify({"error":"El número es obligatorio"}),400
    db=get_db()
    db.execute("INSERT INTO reportes_servicio (numero,departamento,fecha) VALUES(?,?,?)",
               (d["numero"],d.get("departamento",""),d.get("fecha",datetime.date.today().strftime("%d-%m-%y"))))
    db.commit()
    nid = db.execute("SELECT LAST_INSERT_ID() AS id").fetchone()["id"]
    log_event(session.get("nombre_usuario"), "Creación de reporte de servicio",
              f"N° {d['numero']}, dpto {d.get('departamento','')}", ip=_ip())
    db.close()
    return jsonify({"ok":True,"id":nid})

@servicios_bp.route("/reporte_servicio/<int:rid>", methods=["DELETE"])
@login_required
def eliminar_servicio(rid):
    db=get_db()
    db.execute("DELETE FROM reportes_servicio WHERE id=?",(rid,))
    db.commit()
    log_event(session.get("nombre_usuario"), "Eliminación de reporte de servicio",
              f"ID {rid} eliminado", ip=_ip())
    db.close()
    return jsonify({"ok":True})

@servicios_bp.route("/pdf_servicio_blank")
@login_required
def pdf_servicio_blank():
    buf=generar_pdf_servicio_blank()
    log_event(session.get("nombre_usuario"), "Generación PDF de servicio en blanco",
              ip=_ip())
    return send_file(buf,mimetype="application/pdf",as_attachment=True,
                     download_name="ReporteServicio_Blank.pdf")

@servicios_bp.route("/siguiente_numero_servicio")
@login_required
def siguiente_numero_servicio():
    db=get_db()
    anio=datetime.date.today().year
    rows=db.execute("SELECT numero FROM reportes_servicio WHERE fecha_registro LIKE ?",
                    (f"{anio}%",)).fetchall()
    nums=[int(r["numero"].split('-')[1].split('/')[0]) for r in rows if r["numero"] and '-' in r["numero"]]
    siguiente=max(nums)+1 if nums else 1
    db.close()
    log_event(session.get("nombre_usuario"), "Solicitar siguiente número de servicio",
              f"{siguiente}", ip=_ip())
    return jsonify({"numero":f"RS-{siguiente:03d}/{str(anio)[2:]}"})
