from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

from config import Config
from models import db, Usuario, Servicio, Calificacion, SolicitudTrabajo
from models import Servicio

import unicodedata

# ==========================================
# NORMALIZAR TEXTO (sin acentos, lower)
# ==========================================
def normalizar(texto):
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto



app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# --------------------
# RUTA PRINCIPAL SIN LOG
# --------------------
@app.route('/')
def index():
    servicios = Servicio.query.all()
    return render_template('public_dashboard.html', servicios=servicios)

# --------------------
# RUTA PRINCIPAL CON LOG
# --------------------
@app.route('/dashboard')
@login_required
def dashboard():

    servicios = []

    if current_user.rol == 'prestador':
        servicios = Servicio.query.filter_by(usuario_id=current_user.id).all()
    
    from sqlalchemy import and_

    pendientes = 0

    if current_user.rol == 'prestador':
        pendientes = SolicitudTrabajo.query.join(Servicio).filter(
            and_(
                Servicio.usuario_id == current_user.id,
                SolicitudTrabajo.estado == 'pendiente'
            )
        ).count()

    return render_template(
        'dashboard.html',
        usuario=current_user,
        servicios=servicios,
        pendientes=pendientes
    )

# --------------------
# REGISTRO
# --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            email = request.form['email']
            rol = request.form['rol']
            password = generate_password_hash(request.form['password'])

            imagen_file = request.files.get('imagen')
            filename = None

            if imagen_file and imagen_file.filename != '':
                filename = secure_filename(imagen_file.filename)
                ruta = os.path.join('static/uploads', filename)
                imagen_file.save(ruta)

            usuario = Usuario(
                nombre=nombre,
                email=email,
                password=password,
                rol=rol,
                imagen=filename
            )

            db.session.add(usuario)
            db.session.commit()

            flash('Usuario registrado correctamente')
            return redirect(url_for('login'))

        except IntegrityError:
            db.session.rollback()
            flash('Ese email ya está registrado. Probá con otro.', 'danger')

    return render_template('register.html')

# --------------------
# LOGIN
# --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password, password):
            login_user(usuario)
            return redirect(url_for('dashboard'))

        flash('Credenciales incorrectas')

    return render_template('login.html')


# --------------------
# LOGOUT
# --------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))




# --------------------
# CREAR SERVICIO (PRESTADOR)
# --------------------
@app.route('/servicio/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_servicio():

    # Seguridad: solo prestadores
    if current_user.rol != 'prestador':
        flash('Acceso no autorizado')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        categoria = request.form['categoria']

        servicio = Servicio(
            titulo=titulo,
            descripcion=descripcion,
            categoria=categoria,
            usuario_id=current_user.id
        )

        db.session.add(servicio)
        db.session.commit()

        flash('Servicio creado correctamente')
        return redirect(url_for('dashboard'))

    return render_template('nuevo_servicio.html')

# --------------------
# LISTADO DE SERVICIOS (CON BUSCADOR)
# --------------------
@app.route('/servicios')
def servicios():

    query = request.args.get('q', '')

    todos = Servicio.query.all()

    if query:
        query_norm = normalizar(query)

        servicios_filtrados = []

        for s in todos:
            titulo = normalizar(s.titulo)
            categoria = normalizar(s.categoria)

            if query_norm in titulo or query_norm in categoria:
                servicios_filtrados.append(s)

        servicios = servicios_filtrados
    else:
        servicios = todos

    return render_template('servicios.html', servicios=servicios, query=query)

# ==========================================
# API BUSCADOR DE SERVICIOS (AJAX)
# ==========================================
@app.route('/api/buscar_servicios')
def api_buscar_servicios():

    query = request.args.get('q', '')
    query_norm = normalizar(query)

    servicios = Servicio.query.all()
    resultados = []

    for s in servicios:
        titulo_norm = normalizar(s.titulo)
        categoria_norm = normalizar(s.categoria)

        if query_norm in titulo_norm or query_norm in categoria_norm:

            promedio = s.usuario.promedio_estrellas()

            resultados.append({
                "titulo": s.titulo,
                "descripcion": s.descripcion,
                "categoria": s.categoria,
                "prestador": s.usuario.nombre,
                "promedio": promedio if promedio else "Sin calificaciones"
            })

    return jsonify(resultados)

# --------------------
# CALIFICAR SERVICIO
# --------------------
@app.route('/servicio/<int:servicio_id>/calificar', methods=['GET', 'POST'])
@login_required
def calificar_servicio(servicio_id):

    if current_user.rol != 'cliente':
        flash('Solo los clientes pueden calificar servicios')
        return redirect(url_for('dashboard'))

    servicio = Servicio.query.get_or_404(servicio_id)

    if request.method == 'POST':
        estrellas = int(request.form['estrellas'])
        comentario = request.form['comentario']

        calificacion = Calificacion(
            estrellas=estrellas,
            comentario=comentario,
            usuario_id=current_user.id,
            servicio_id=servicio.id
        )

        db.session.add(calificacion)
        db.session.commit()

        flash('Calificación enviada correctamente')
        return redirect(url_for('servicios'))

    return render_template('calificar_servicio.html', servicio=servicio)

# --------------------
# EDITAR PERFIL
# --------------------
import os
from werkzeug.utils import secure_filename

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():

    if request.method == 'POST':
        current_user.nombre = request.form['nombre']
        current_user.email = request.form['email']

        # Imagen
        imagen = request.files.get('imagen')
        if imagen and imagen.filename != '':
            filename = secure_filename(imagen.filename)
            ruta = os.path.join('static/uploads', filename)
            imagen.save(ruta)
            current_user.imagen = filename

        db.session.commit()
        flash('Perfil actualizado correctamente')
        return redirect(url_for('dashboard'))

    return render_template('perfil.html', usuario=current_user)

# --------------------
# EDITAR SERVICIO (PRESTADOR)
# --------------------
@app.route('/servicio/<int:servicio_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_servicio(servicio_id):

    servicio = Servicio.query.get_or_404(servicio_id)

    # Seguridad: solo el prestador dueño del servicio
    if current_user.rol != 'prestador' or servicio.usuario_id != current_user.id:
        flash('Acceso no autorizado')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        servicio.titulo = request.form['titulo']
        servicio.descripcion = request.form['descripcion']
        servicio.categoria = request.form['categoria']

        db.session.commit()
        flash('Servicio actualizado correctamente')
        return redirect(url_for('dashboard'))

    return render_template('editar_servicio.html', servicio=servicio)
# --------------------
# CALIFICACIONES 
# --------------------
@app.route('/mis-calificaciones')
@login_required
def mis_calificaciones():

    # Si es PRESTADOR → ver calificaciones recibidas
    if current_user.rol == 'prestador':
        calificaciones = Calificacion.query.join(Servicio).filter(
            Servicio.usuario_id == current_user.id
        ).all()

        titulo = "Calificaciones recibidas"

    # Si es CLIENTE → ver calificaciones realizadas
    else:
        calificaciones = Calificacion.query.filter_by(
            usuario_id=current_user.id
        ).all()

        titulo = "Mis calificaciones realizadas"

    return render_template(
        'mis_calificaciones.html',
        calificaciones=calificaciones,
        titulo=titulo
    )

# --------------------
# RUTA DEL PERFIL PÚBLICO
# --------------------
@app.route('/prestador/<int:usuario_id>')
def perfil_prestador(usuario_id):

    prestador = Usuario.query.get_or_404(usuario_id)
    servicios = Servicio.query.filter_by(usuario_id=prestador.id).all()

    return render_template(
        'perfil_prestador.html',
        prestador=prestador,
        servicios=servicios
    )
# =========================
# NORMALIZAR TEXTO (sin acentos y minúsculas)
# =========================
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

# =========================
# Contratar servicio
# =========================
from werkzeug.utils import secure_filename
import os

@app.route('/contratar/<int:servicio_id>', methods=['GET', 'POST'])
@login_required
def contratar_servicio(servicio_id):

    servicio = Servicio.query.get_or_404(servicio_id)

    if request.method == 'POST':
        descripcion = request.form['descripcion']

        archivo = request.files.get('archivo')
        filename = None

        if archivo and archivo.filename != '':
            filename = secure_filename(archivo.filename)
            ruta = os.path.join('static/uploads', filename)
            archivo.save(ruta)

        solicitud = SolicitudTrabajo(
            descripcion=descripcion,
            archivo=filename,
            cliente_id=current_user.id,
            servicio_id=servicio.id
        )

        db.session.add(solicitud)
        db.session.commit()

        flash('Solicitud enviada al prestador')
        return redirect(url_for('servicios'))

    return render_template('contratar_servicio.html', servicio=servicio)

# =========================
# SOLICITUD DE SERVICIO
# =========================
@app.route('/solicitudes')
@login_required
def ver_solicitudes():

    if current_user.rol != 'prestador':
        flash('Acceso no autorizado')
        return redirect(url_for('dashboard'))

    solicitudes = SolicitudTrabajo.query.join(Servicio).filter(
        Servicio.usuario_id == current_user.id
    ).all()

    return render_template(
        'solicitudes.html',
        solicitudes=solicitudes
    )

# =========================
# ACEPTAR O RECHAZAR SOLICITUD
# =========================
@app.route('/solicitud/<int:solicitud_id>/<accion>')
@login_required
def gestionar_solicitud(solicitud_id, accion):

    solicitud = SolicitudTrabajo.query.get_or_404(solicitud_id)

    if current_user.rol != 'prestador':
        flash('Acceso no autorizado')
        return redirect(url_for('dashboard'))

    if accion == 'aceptar':
        solicitud.estado = 'aceptado'

    elif accion == 'rechazar':
        solicitud.estado = 'rechazado'

    elif accion == 'realizado':
        solicitud.estado = 'realizado'

    db.session.commit()
    flash('Solicitud actualizada')

    return redirect(url_for('ver_solicitudes'))

# --------------------
# CALIFICAR SERVICIO
# --------------------
@app.route('/calificar/<int:solicitud_id>', methods=['GET', 'POST'])
@login_required
def calificar_trabajo(solicitud_id):

    solicitud = SolicitudTrabajo.query.get_or_404(solicitud_id)

    if current_user.rol != 'cliente' or solicitud.cliente_id != current_user.id:
        flash('Acceso no autorizado')
        return redirect(url_for('dashboard'))

    if solicitud.estado != 'realizado':
        flash('Aún no podés calificar este trabajo')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        calificacion = Calificacion(
            precio=int(request.form['precio']),
            calidad=int(request.form['calidad']),
            amabilidad=int(request.form['amabilidad']),
            comentario=request.form['comentario'],
            usuario_id=current_user.id,
            servicio_id=solicitud.servicio_id
        )

        solicitud.estado = 'calificado'

        db.session.add(calificacion)
        db.session.commit()

        flash('Gracias por calificar el servicio')
        return redirect(url_for('dashboard'))

    return render_template(
        'calificar_trabajo.html',
        solicitud=solicitud
    )

# --------------------
# MOSTRAR SERVICIO A CALIFICAR
# --------------------
@app.route('/mis-solicitudes')
@login_required
def mis_solicitudes():

    if current_user.rol != 'cliente':
        flash('Acceso no autorizado')
        return redirect(url_for('dashboard'))

    solicitudes = SolicitudTrabajo.query.filter_by(
        cliente_id=current_user.id
    ).all()

    return render_template(
        'mis_solicitudes.html',
        solicitudes=solicitudes
    )

# --------------------
# EJECUCIÓN
# --------------------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

