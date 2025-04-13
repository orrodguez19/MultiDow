import os
import logging
import requests
from flask import Flask
from deltachat import Account, Config, Chat, Message, DC_EVENT_MSG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deltachat_bot")

# Ruta donde se guardarán los datos de DeltaChat
DC_PATH = "./dc_storage"

# Datos de la cuenta
EMAIL = "orrodriguez588@gmail.com"
PASSWORD = "cnkpjyridpqcbclu"

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

# Función para subir archivos a Uguu
def subir_a_uguu(file_path):
    try:
        with open(file_path, "rb") as f:
            files = {"files[]": f}
            response = requests.post("https://uguu.se/upload.php", files=files)
        if response.ok:
            return response.json()["files"][0]["url"], None
        else:
            return None, f"Error HTTP {response.status_code}"
    except Exception as e:
        return None, str(e)

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
                chat.send_text(f"¡Hola {name}! Envíame un archivo y te daré un enlace para descargarlo.")
            elif text == "/help":
                chat.send_text("Comandos:\n/start - Inicia\n/help - Ayuda\nEnvía un archivo para subirlo.")
            else:
                chat.send_text(f"No entendí el mensaje, {name}. Usa /help para ver comandos.")

        file_path = msg.get_file()
        if file_path and os.path.exists(file_path):
            chat.send_text("Subiendo tu archivo...")
            link, error = subir_a_uguu(file_path)
            if link:
                chat.send_text(f"Aquí está tu archivo:\n{link}")
            else:
                chat.send_text(f"No se pudo subir tu archivo: {error}")
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