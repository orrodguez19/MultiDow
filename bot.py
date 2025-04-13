import os
import logging
import requests
import yt_dlp
from flask import Flask
from deltachat import Account, Config, Chat, Message, DC_EVENT_MSG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deltachat_bot")

# Ruta donde se guardarán los datos de DeltaChat
DC_PATH = "./dc_storage"

# Datos de la cuenta (usa variables de entorno en producción)
EMAIL = "orrodriguez588@gmail.com"
PASSWORD = "cnkpjyridpqcbclu"

# Ruta donde se guardará el video descargado temporalmente
TEMP_VIDEO_PATH = "/tmp/video.mp4"

# Crear cuenta de Delta Chat
account = Account(DC_PATH)

def setup_account():
    logger.info("Configurando cuenta...")
    config = Config(account)
    config.set_config("addr", EMAIL)
    config.set_config("mail_pw", PASSWORD)
    config.set_config("bot", "1")
    config.set_config("send_receipts", "1")
    config.set_config("watch", "1")
    config.set_config("e2ee_enabled", "1")
    config.set_config("show_emails", "1")
    account.set_config(config)

    account.configure()
    logger.info("Cuenta conectada correctamente")

# Función para descargar el video usando yt-dlp
def download_video(url):
    options = {
        'format': 'bestvideo+bestaudio/best',  # Mejor calidad de video y audio
        'outtmpl': TEMP_VIDEO_PATH,            # Guardar el archivo en la ruta temporal
    }
    
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

# Callback para manejar mensajes
def message_callback(event, chat_id, msg_id):
    if event != DC_EVENT_MSG:
        return

    try:
        msg = Message(account, msg_id)
        chat = Chat(account, chat_id)
        contact = msg.get_sender_contact()
        name = contact.display_name or contact.addr or "Usuario"

        if msg.text:
            text = msg.text.strip().lower()
            if text == "/start":
                chat.send_text(f"¡Hola {name}! Envíame un enlace de video y te lo enviaré de vuelta.")
            elif text == "/help":
                chat.send_text("Comandos:\n/start - Inicia\n/help - Ayuda\nEnvía un enlace de video para que lo descargue.")
            else:
                chat.send_text(f"No entendí el mensaje, {name}. Usa /help para ver comandos.")

        if 'http' in msg.text:  # Verifica si el mensaje contiene un enlace
            try:
                chat.send_text("Descargando el video...")
                download_video(msg.text)  # Llama a la función para descargar el video
                chat.send_text("Enviando el video...")
                chat.send_file(TEMP_VIDEO_PATH)  # Envía el archivo de video

                # Elimina el archivo después de enviarlo
                os.remove(TEMP_VIDEO_PATH)
            except Exception as e:
                chat.send_text(f"Hubo un error al descargar o enviar el video: {str(e)}")
    except Exception as e:
        logger.error(f"Error al procesar mensaje: {e}")

# Iniciar el bot
def start_bot():
    setup_account()
    account.set_event_handler(message_callback)
    logger.info("Bot escuchando mensajes...")

# Servidor Flask (puerto 10000 para Render)
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot DeltaChat activo."

if __name__ == "__main__":
    start_bot()
    logger.info("Servidor Flask corriendo en puerto 10000")
    app.run(host="0.0.0.0", port=10000)