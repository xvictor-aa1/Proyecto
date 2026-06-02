from flask import Blueprint, request, jsonify, session
from database import get_db
from modulos.auth import login_required

#Modulo de auditorias
auditoria_bp = Blueprint('auditoria', __name__)

@auditoria_bp.route("/auditoria", methods=["GET"])
@login_required
def listar_auditoria():
    if session.get("rol_usuario") != "superadmin":
        return jsonify({"error": "Solo el superadministrador puede ver la auditoría"}), 403

    user_id = request.args.get("user_id")
    accion  = request.args.get("accion")
    desde   = request.args.get("desde")    # formato YYYY-MM-DD
    hasta   = request.args.get("hasta")

    db = get_db()
    query = """
        SELECT a.id, a.user_id, u.nombre_completo, a.accion, a.detalle, a.fecha
        FROM auditoria a
        JOIN usuarios u ON a.user_id = u.id
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND a.user_id = ?"
        params.append(int(user_id))
    if accion:
        query += " AND a.accion = ?"
        params.append(accion)
    if desde:
        query += " AND DATE(a.fecha) >= ?"
        params.append(desde)
    if hasta:
        query += " AND DATE(a.fecha) <= ?"
        params.append(hasta)

    query += " ORDER BY a.fecha DESC LIMIT 500"
    rows = db.execute(query, params).fetchall()
    db.close()
    return jsonify(rows)
