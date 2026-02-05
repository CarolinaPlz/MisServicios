from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# =========================
# USUARIO
# =========================
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    imagen = db.Column(db.String(200))

    # Relación SOLO con calificaciones
    calificaciones = db.relationship('Calificacion', backref='cliente', lazy=True)

    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    # PROMEDIO GENERAL DEL PRESTADOR
    def promedio_estrellas(self):
        total = 0
        cantidad = 0

        for servicio in self.servicios:
            for c in servicio.calificaciones:
                promedio_c = (c.precio + c.calidad + c.amabilidad) / 3
                total += promedio_c
                cantidad += 1

        if cantidad == 0:
            return None

        return round(total / cantidad, 1)


# =========================
# SERVICIO
# =========================
class Servicio(db.Model):
    __tablename__ = 'servicios'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False
    )

    # ✅ ÚNICA relación con Usuario (LA CORRECTA)
    usuario = db.relationship('Usuario', backref='servicios', lazy=True)

    # Relación con calificaciones
    calificaciones = db.relationship(
        'Calificacion',
        backref='servicio',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def promedio_estrellas(self):
        if not self.calificaciones:
            return None

        total = 0
        cantidad = 0

        for c in self.calificaciones:
            promedio_c = (c.precio + c.calidad + c.amabilidad) / 3
            total += promedio_c
            cantidad += 1

        return round(total / cantidad, 1)


# =========================
# CALIFICACIÓN
# =========================
class Calificacion(db.Model):
    __tablename__ = 'calificaciones'

    id = db.Column(db.Integer, primary_key=True)

    precio = db.Column(db.Integer, nullable=False)
    calidad = db.Column(db.Integer, nullable=False)
    amabilidad = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.Text)

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicios.id'))

# =========================
# Solicitud de trabajo
# =========================
class SolicitudTrabajo(db.Model):
    __tablename__ = 'solicitudes_trabajo'

    id = db.Column(db.Integer, primary_key=True)

    descripcion = db.Column(db.Text, nullable=False)
    archivo = db.Column(db.String(200))

    estado = db.Column(db.String(30), default='pendiente')
    # pendiente | aceptado | realizado | calificado

    cliente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicios.id'))

    cliente = db.relationship('Usuario', backref='solicitudes')
    servicio = db.relationship('Servicio', backref='solicitudes')
