from flask import Flask, request, jsonify, render_template
from flask_mail import Mail, Message
from celery import Celery
import requests

# Configuración para Flask-Mail
app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@example.com'
app.config['MAIL_PASSWORD'] = 'tu_contraseña'
mail = Mail(app)

# Configuración para Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


@celery.task
def enviar_correo_async(asunto, destinatario, cuerpo):
    with app.app_context():
        msg = Message(asunto, sender=app.config['MAIL_USERNAME'], recipients=[destinatario])
        msg.body = cuerpo
        mail.send(msg)

# Servicio REST para manejar las recetas
RECETAS_API_URL = "http://api.example.com/recetas" 

# Ruta para la página principal
@app.route('/')
def home():
    response = requests.get(RECETAS_API_URL)
    if response.status_code == 200:
        recetas = response.json()
        return render_template('index.html', recetas=recetas)
    else:
        return render_template('error.html', mensaje="Error al obtener recetas."), 500

# Ruta para agregar una receta
@app.route('/recetas', methods=['POST'])
def agregar_receta():
    nombre = request.form.get('nombre')
    ingredientes = request.form.get('ingredientes')
    pasos = request.form.get('pasos')

    if not (nombre and ingredientes and pasos):
        return jsonify({"error": "Faltan datos de la receta"}), 400

    receta = {
        "nombre": nombre,
        "ingredientes": ingredientes,
        "pasos": pasos
    }
    response = requests.post(RECETAS_API_URL, json=receta)

    if response.status_code == 201:
        # Enviar correo de notificación de manera asíncrona
        asunto = "Nueva receta agregada"
        destinatario = "destinatario@example.com"
        cuerpo = f"Se ha agregado una nueva receta: {nombre}"
        enviar_correo_async.delay(asunto, destinatario, cuerpo)
        return jsonify({"message": "Receta agregada con éxito y notificación enviada."}), 201
    else:
        return jsonify({"error": "Error al agregar la receta."}), response.status_code

# Ruta para actualizar una receta existente
@app.route('/recetas/<nombre>', methods=['GET', 'POST'])
def actualizar_receta(nombre):
    if request.method == 'GET':
        response = requests.get(f"{RECETAS_API_URL}/{nombre}")
        if response.status_code == 200:
            receta = response.json()
            return render_template('editar.html', receta=receta)
        else:
            return render_template('error.html', mensaje="Receta no encontrada."), 404
    else:
        nuevo_nombre = request.form.get("nombre")
        nuevos_ingredientes = request.form.get("ingredientes")
        nuevos_pasos = request.form.get("pasos")

        receta = {
            "nombre": nuevo_nombre,
            "ingredientes": nuevos_ingredientes,
            "pasos": nuevos_pasos
        }
        response = requests.put(f"{RECETAS_API_URL}/{nombre}", json=receta)

        if response.status_code == 200:
            # Enviar correo de notificación de manera asíncrona
            asunto = "Receta actualizada"
            destinatario = "destinatario@example.com"
            cuerpo = f"La receta {nombre} ha sido actualizada."
            enviar_correo_async.delay(asunto, destinatario, cuerpo)
            return render_template('success.html', mensaje="Receta actualizada con éxito.")
        else:
            return render_template('error.html', mensaje="Error al actualizar la receta."), response.status_code

# Ruta para eliminar una receta existente
@app.route('/recetas/<nombre>/eliminar', methods=['POST'])
def eliminar_receta(nombre):
    response = requests.delete(f"{RECETAS_API_URL}/{nombre}")

    if response.status_code == 200:
        # Enviar correo de notificación de manera asíncrona
        asunto = "Receta eliminada"
        destinatario = "destinatario@example.com"
        cuerpo = f"La receta {nombre} ha sido eliminada."
        enviar_correo_async.delay(asunto, destinatario, cuerpo)
        return render_template('success.html', mensaje="Receta eliminada con éxito.")
    else:
        return render_template('error.html', mensaje="Receta no encontrada."), 404

# Ruta para buscar una receta por nombre
@app.route('/recetas/<nombre>', methods=['GET'])
def buscar_receta(nombre):
    response = requests.get(f"{RECETAS_API_URL}/{nombre}")

    if response.status_code == 200:
        receta = response.json()
        return render_template('detalle.html', receta=receta)
    else:
        return render_template('error.html', mensaje="Receta no encontrada."), 404

# Archivo principal de ejecución
if __name__ == '__main__':
    app.run()
