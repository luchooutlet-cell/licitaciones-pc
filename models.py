from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class Licitacion(db.Model):
    __tablename__ = "licitaciones"
    id = db.Column(db.Integer, primary_key=True)

    # Identificación
    codigo_interno = db.Column(db.String(50), unique=True)
    nro_licitacion = db.Column(db.String(100))
    cliente = db.Column(db.String(150), nullable=False)
    yacimiento = db.Column(db.String(150))
    provincia = db.Column(db.String(80))

    # Fechas
    fecha_publicacion = db.Column(db.Date)
    fecha_apertura = db.Column(db.Date)
    fecha_cierre = db.Column(db.Date)
    fecha_adjudicacion = db.Column(db.Date)

    # Estado y tipo
    estado = db.Column(db.String(50), default="En análisis")
    tipo_servicio = db.Column(db.String(120))
    descripcion = db.Column(db.Text)
    plazo_ejecucion = db.Column(db.String(100))
    modalidad = db.Column(db.String(100))

    # Económico
    moneda = db.Column(db.String(10), default="USD")
    presupuesto_oficial = db.Column(db.Numeric(18, 2))
    nuestra_oferta = db.Column(db.Numeric(18, 2))
    monto_adjudicado = db.Column(db.Numeric(18, 2))
    clausula_ajuste = db.Column(db.String(150))
    formula_ajuste = db.Column(db.Text)
    forma_pago = db.Column(db.String(200))

    # Técnico
    servicios_incluidos = db.Column(db.Text)
    equipos_requeridos = db.Column(db.Text)
    normativa = db.Column(db.String(300))
    subcontratos = db.Column(db.Text)

    # Técnico específico de Protección Catódica
    km_ducto = db.Column(db.Float)
    tipo_recubrimiento = db.Column(db.String(100))
    cantidad_pozos = db.Column(db.Integer)
    resistividad_suelo = db.Column(db.Float)
    potencial_on = db.Column(db.Float)
    potencial_off = db.Column(db.Float)
    sistema_pc = db.Column(db.String(100))
    vida_util_anodo = db.Column(db.Integer)

    # Comercial
    contacto_cliente = db.Column(db.String(200))
    email_contacto = db.Column(db.String(150))
    tel_contacto = db.Column(db.String(80))
    fecha_consultas = db.Column(db.Date)
    garantia_oferta = db.Column(db.String(150))
    garantia_cumplimiento = db.Column(db.String(150))
    competidores = db.Column(db.Text)
    documentacion_entregada = db.Column(db.Text)
    notas = db.Column(db.Text)

    # Meta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def dias_para_cierre(self):
        if not self.fecha_cierre:
            return None
        return (self.fecha_cierre - datetime.utcnow().date()).days


class Adjunto(db.Model):
    __tablename__ = "adjuntos"
    id = db.Column(db.Integer, primary_key=True)
    licitacion_id = db.Column(db.Integer, db.ForeignKey("licitaciones.id"), nullable=False)
    nombre_original = db.Column(db.String(255), nullable=False)
    nombre_guardado = db.Column(db.String(255), nullable=False)
    tipo_mime = db.Column(db.String(120))
    tamano_bytes = db.Column(db.Integer)
    descripcion = db.Column(db.String(255))
    subido_en = db.Column(db.DateTime, default=datetime.utcnow)

    licitacion = db.relationship("Licitacion", backref=db.backref("adjuntos", cascade="all, delete-orphan"))


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(100))
    rol = db.Column(db.String(20), default="usuario")
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
        
    @property
    def is_active(self):
        return self.activo


class Historial(db.Model):
    __tablename__ = "historial"
    id = db.Column(db.Integer, primary_key=True)
    licitacion_id = db.Column(db.Integer, db.ForeignKey("licitaciones.id"), nullable=False)
    usuario = db.Column(db.String(100), nullable=False)
    accion = db.Column(db.String(100), nullable=False)
    detalle = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    licitacion = db.relationship("Licitacion", backref=db.backref("historial", cascade="all, delete-orphan", order_by="Historial.fecha.desc()"))


class TipoServicio(db.Model):
    __tablename__ = "tipos_servicio"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), unique=True, nullable=False)


class EstadoLicitacion(db.Model):
    __tablename__ = "estados_licitacion"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)