import os
import uuid
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, Response
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func
from models import db, Licitacion, Adjunto, Usuario

app = Flask(__name__)
app.config["SECRET_KEY"] = "cambiar-esta-clave-mas-adelante"
db_url = os.environ.get("DATABASE_URL", "sqlite:///licitaciones.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB por archivo
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# --- CONFIGURACIÓN DE EMAIL ---
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USERNAME"] = "tu_correo@gmail.com"       # <-- CAMBIAR
app.config["MAIL_PASSWORD"] = "abcdefghijklmnop"          # <-- CAMBIAR
app.config["MAIL_DESTINATARIO"] = "tu_correo@gmail.com"   # <-- CAMBIAR

db.init_app(app)

# --- CONFIGURACIÓN DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Por favor, iniciá sesión para acceder."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- LISTAS PARA DESPLEGABLES ---
TIPOS_SERVICIO = [
    "Relevamiento e ingeniería de PC",
    "Instalación corriente impresa",
    "Instalación ánodos galvánicos",
    "Rehabilitación lechos de ánodos",
    "Medición CIPS / DCVG / PCM",
    "Mantenimiento de sistemas",
    "Instalación rectificadores / TRUs",
    "Monitoreo remoto",
    "Evaluación de interferencias",
    "Diseño PC ductos nuevos",
    "Puesta en marcha",
    "Capacitación técnica",
]
ESTADOS = ["En análisis", "Preparando oferta", "Enviada", "Adjudicada", "Perdida", "Desierta"]
MONEDAS = ["USD", "ARS", "EUR"]


# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = Usuario.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            flash(f"¡Bienvenido/a, {user.nombre or user.username}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos, o cuenta inactiva.", "danger")
            
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


# ==========================================
# RUTAS PRINCIPALES
# ==========================================
@app.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    tipo = request.args.get("tipo", "")

    query = Licitacion.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Licitacion.cliente.ilike(like),
            Licitacion.nro_licitacion.ilike(like),
            Licitacion.yacimiento.ilike(like),
            Licitacion.descripcion.ilike(like),
        ))
    if estado:
        query = query.filter_by(estado=estado)
    if tipo:
        query = query.filter_by(tipo_servicio=tipo)

    licitaciones = query.order_by(Licitacion.fecha_cierre.asc().nullslast()).all()
    return render_template(
        "index.html",
        licitaciones=licitaciones,
        estados=ESTADOS,
        tipos=TIPOS_SERVICIO,
        q=q,
        estado_sel=estado,
        tipo_sel=tipo,
    )


@app.route("/nueva", methods=["GET", "POST"])
@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def form(id=None):
    lic = Licitacion.query.get_or_404(id) if id else Licitacion()

    if request.method == "POST":
        f = request.form

        campos_texto = [
            "codigo_interno", "nro_licitacion", "cliente", "yacimiento", "provincia",
            "estado", "tipo_servicio", "descripcion", "plazo_ejecucion", "modalidad",
            "moneda", "clausula_ajuste", "formula_ajuste", "forma_pago",
            "servicios_incluidos", "equipos_requeridos", "normativa", "subcontratos",
            "contacto_cliente", "email_contacto", "tel_contacto",
            "garantia_oferta", "garantia_cumplimiento", "competidores",
            "documentacion_entregada", "notas", "tipo_recubrimiento", "sistema_pc",
        ]
        for campo in campos_texto:
            setattr(lic, campo, f.get(campo) or None)

        for campo in ["presupuesto_oficial", "nuestra_oferta", "monto_adjudicado"]:
            valor = f.get(campo)
            setattr(lic, campo, float(valor) if valor else None)

        for campo in ["km_ducto", "resistividad_suelo", "potencial_on", "potencial_off"]:
            valor = f.get(campo)
            setattr(lic, campo, float(valor) if valor else None)
            
        for campo in ["cantidad_pozos", "vida_util_anodo"]:
            valor = f.get(campo)
            setattr(lic, campo, int(valor) if valor else None)

        for campo in ["fecha_publicacion", "fecha_apertura", "fecha_cierre",
                      "fecha_adjudicacion", "fecha_consultas"]:
            valor = f.get(campo)
            setattr(lic, campo, datetime.strptime(valor, "%Y-%m-%d").date() if valor else None)

        if not id:
            db.session.add(lic)
        db.session.commit()
        flash("Licitación guardada correctamente", "success")
        return redirect(url_for("detalle", id=lic.id))

    return render_template(
        "form.html",
        lic=lic,
        estados=ESTADOS,
        tipos=TIPOS_SERVICIO,
        monedas=MONEDAS,
    )


@app.route("/detalle/<int:id>")
@login_required
def detalle(id):
    lic = Licitacion.query.get_or_404(id)
    return render_template("detalle.html", lic=lic)


@app.route("/eliminar/<int:id>", methods=["POST"])
@login_required
def eliminar(id):
    if current_user.rol != "admin":
        flash("Solo los administradores pueden eliminar licitaciones.", "danger")
        return redirect(url_for("index"))
        
    lic = Licitacion.query.get_or_404(id)
    db.session.delete(lic)
    db.session.commit()
    flash("Licitación eliminada", "warning")
    return redirect(url_for("index"))


# ==========================================
# RUTAS DE ADJUNTOS
# ==========================================
@app.route("/licitacion/<int:id>/adjuntar", methods=["POST"])
@login_required
def adjuntar(id):
    lic = Licitacion.query.get_or_404(id)
    archivo = request.files.get("archivo")
    descripcion = request.form.get("descripcion", "").strip() or None

    if not archivo or archivo.filename == "":
        flash("No seleccionaste ningún archivo", "warning")
        return redirect(url_for("detalle", id=id))

    nombre_original = archivo.filename
    nombre_seguro = secure_filename(nombre_original)
    nombre_guardado = f"{uuid.uuid4().hex}_{nombre_seguro}"

    ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre_guardado)
    archivo.save(ruta)
    tamano = os.path.getsize(ruta)

    adjunto = Adjunto(
        licitacion_id=lic.id,
        nombre_original=nombre_original,
        nombre_guardado=nombre_guardado,
        tipo_mime=archivo.mimetype,
        tamano_bytes=tamano,
        descripcion=descripcion,
    )
    db.session.add(adjunto)
    db.session.commit()
    flash(f"Archivo '{nombre_original}' subido correctamente", "success")
    return redirect(url_for("detalle", id=id))


@app.route("/adjunto/<int:id>/descargar")
@login_required
def descargar_adjunto(id):
    adj = Adjunto.query.get_or_404(id)
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        adj.nombre_guardado,
        as_attachment=True,
        download_name=adj.nombre_original,
    )


@app.route("/adjunto/<int:id>/eliminar", methods=["POST"])
@login_required
def eliminar_adjunto(id):
    adj = Adjunto.query.get_or_404(id)
    lic_id = adj.licitacion_id
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], adj.nombre_guardado)
    if os.path.exists(ruta):
        os.remove(ruta)
    db.session.delete(adj)
    db.session.commit()
    flash("Adjunto eliminado", "warning")
    return redirect(url_for("detalle", id=lic_id))


# ==========================================
# DASHBOARD Y EXPORTACIÓN
# ==========================================
@app.route("/dashboard")
@login_required
def dashboard():
    hoy = datetime.utcnow().date()
    total_licitaciones = Licitacion.query.count()
    total_adjudicadas = Licitacion.query.filter_by(estado="Adjudicada").count()
    total_en_proceso = Licitacion.query.filter(
        Licitacion.estado.in_(["En análisis", "Preparando oferta", "Enviada"])
    ).count()

    tasa_adjudicacion = round((total_adjudicadas / total_licitaciones) * 100, 1) if total_licitaciones > 0 else 0.0

    cierres_proximos = Licitacion.query.filter(
        Licitacion.fecha_cierre.isnot(None),
        Licitacion.fecha_cierre >= hoy,
        Licitacion.fecha_cierre <= hoy + timedelta(days=7)
    ).count()

    monto_total_ofertado = db.session.query(
        func.coalesce(func.sum(Licitacion.nuestra_oferta), 0)
    ).scalar() or 0

    monto_total_adjudicado = db.session.query(
        func.coalesce(func.sum(Licitacion.monto_adjudicado), 0)
    ).scalar() or 0

    ticket_promedio = round(float(monto_total_ofertado) / total_licitaciones, 2) if total_licitaciones > 0 else 0.0

    por_estado = db.session.query(
        Licitacion.estado, func.count(Licitacion.id).label("cantidad")
    ).group_by(Licitacion.estado).order_by(func.count(Licitacion.id).desc()).all()

    top_clientes = db.session.query(
        Licitacion.cliente,
        func.count(Licitacion.id).label("cantidad"),
        func.coalesce(func.sum(Licitacion.nuestra_oferta), 0).label("monto"),
    ).group_by(Licitacion.cliente).order_by(func.count(Licitacion.id).desc()).limit(8).all()

    por_tipo = db.session.query(
        Licitacion.tipo_servicio, func.count(Licitacion.id).label("cantidad")
    ).group_by(Licitacion.tipo_servicio).order_by(func.count(Licitacion.id).desc()).all()

    proximos_cierres = Licitacion.query.filter(
        Licitacion.fecha_cierre.isnot(None),
        Licitacion.fecha_cierre >= hoy,
        Licitacion.fecha_cierre <= hoy + timedelta(days=15)
    ).order_by(Licitacion.fecha_cierre.asc()).all()

    return render_template(
        "dashboard.html",
        total_licitaciones=total_licitaciones,
        total_adjudicadas=total_adjudicadas,
        total_en_proceso=total_en_proceso,
        tasa_adjudicacion=tasa_adjudicacion,
        cierres_proximos=cierres_proximos,
        monto_total_ofertado=float(monto_total_ofertado),
        monto_total_adjudicado=float(monto_total_adjudicado),
        ticket_promedio=ticket_promedio,
        por_estado=por_estado,
        top_clientes=top_clientes,
        por_tipo=por_tipo,
        proximos_cierres=proximos_cierres,
    )


@app.route("/exportar/excel")
@login_required
def exportar_excel():
    import csv
    from io import StringIO

    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    tipo = request.args.get("tipo", "")

    query = Licitacion.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            Licitacion.cliente.ilike(like),
            Licitacion.nro_licitacion.ilike(like),
            Licitacion.yacimiento.ilike(like),
            Licitacion.descripcion.ilike(like),
        ))
    if estado:
        query = query.filter_by(estado=estado)
    if tipo:
        query = query.filter_by(tipo_servicio=tipo)

    licitaciones = query.order_by(Licitacion.fecha_cierre.asc().nullslast()).all()

    output = StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "Código interno", "N° licitación", "Cliente", "Yacimiento", "Provincia",
        "Estado", "Tipo servicio", "Modalidad", "Fecha cierre", "Días para cierre",
        "Plazo ejecución", "Moneda", "Presupuesto oficial", "Nuestra oferta",
        "Monto adjudicado", "Cláusula ajuste", "Fórmula ajuste", "Forma de pago",
        "Servicios incluidos", "Equipos requeridos", "Normativa", "Subcontratos",
        "Contacto", "Email", "Teléfono", "Garantía oferta", "Garantía cumplimiento",
        "Competidores", "Documentación entregada", "Notas",
    ])

    for l in licitaciones:
        writer.writerow([
            l.codigo_interno or "", l.nro_licitacion or "", l.cliente or "", l.yacimiento or "",
            l.provincia or "", l.estado or "", l.tipo_servicio or "", l.modalidad or "",
            l.fecha_cierre.strftime("%Y-%m-%d") if l.fecha_cierre else "",
            l.dias_para_cierre if l.dias_para_cierre is not None else "",
            l.plazo_ejecucion or "", l.moneda or "",
            float(l.presupuesto_oficial) if l.presupuesto_oficial else "",
            float(l.nuestra_oferta) if l.nuestra_oferta else "",
            float(l.monto_adjudicado) if l.monto_adjudicado else "",
            l.clausula_ajuste or "", l.formula_ajuste or "", l.forma_pago or "",
            l.servicios_incluidos or "", l.equipos_requeridos or "", l.normativa or "",
            l.subcontratos or "", l.contacto_cliente or "", l.email_contacto or "",
            l.tel_contacto or "", l.garantia_oferta or "", l.garantia_cumplimiento or "",
            l.competidores or "", l.documentacion_entregada or "", l.notas or "",
        ])

    csv_data = output.getvalue()
    output.close()

    from datetime import date
    nombre_archivo = f"licitaciones_{date.today().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )


# ==========================================
# EMAILS
# ==========================================
def enviar_email_alerta(licitaciones, asunto, mensaje_intro):
    if not licitaciones:
        return False

    msg = MIMEMultipart()
    msg["From"] = app.config["MAIL_USERNAME"]
    msg["To"] = app.config["MAIL_DESTINATARIO"]
    msg["Subject"] = asunto

    html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #0d6efd;">🔔 Alerta de Licitaciones · Protección Catódica</h2>
        <p>{mensaje_intro}</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
          <thead style="background-color: #343a40; color: white;">
            <tr><th>Nro Licitación</th><th>Cliente</th><th>Cierre</th><th>Días</th><th>Estado</th></tr>
          </thead><tbody>
    """
    
    for l in licitaciones:
        dias = l.dias_para_cierre
        color = "#dc3545" if dias <= 3 else "#ffc107" if dias <= 7 else "#198754"
        text_color = "#fff" if dias <= 3 or dias > 7 else "#000"
        html += f"""<tr>
              <td>{l.nro_licitacion or l.codigo_interno or l.id}</td>
              <td>{l.cliente}</td>
              <td>{l.fecha_cierre}</td>
              <td style="background-color: {color}; color: {text_color}; text-align: center; font-weight: bold;">{dias}d</td>
              <td>{l.estado}</td>
            </tr>"""
    
    html += """</tbody></table><p style="margin-top: 20px; font-size: 12px; color: #777;">Este es un mensaje automático del Sistema de Licitaciones PC.</p></body></html>"""
    
    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP(app.config["MAIL_SERVER"], app.config["MAIL_PORT"])
        server.starttls()
        server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False


@app.route("/enviar_alertas", methods=["POST"])
@login_required
def enviar_alertas():
    hoy = datetime.utcnow().date()
    proximas = Licitacion.query.filter(
        Licitacion.fecha_cierre.isnot(None),
        Licitacion.fecha_cierre >= hoy,
        Licitacion.fecha_cierre <= hoy + timedelta(days=7),
        Licitacion.estado.in_(["En análisis", "Preparando oferta", "Enviada"])
    ).order_by(Licitacion.fecha_cierre.asc()).all()

    if not proximas:
        flash("No hay licitaciones próximas a vencer (≤7 días) para alertar.", "info")
        return redirect(url_for("dashboard"))

    exito = enviar_email_alerta(
        proximas,
        "🔔 Alerta: Licitaciones por vencer esta semana",
        f"Tenés <b>{len(proximas)}</b> licitación(es) que cierran en los próximos 7 días."
    )

    if exito:
        flash(f"Se envió el email con {len(proximas)} licitaciones a {app.config['MAIL_DESTINATARIO']}", "success")
    else:
        flash("Error al enviar el email. Revisá la configuración y la terminal.", "danger")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
    db_url = os.environ.get("DATABASE_URL", "sqlite:///licitaciones.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Forzar el uso del driver psycopg2 si es una URL de PostgreSQL
if db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url