import os
import threading
import time
from flask import Flask, render_template
import requests
from deltachat import Account, Chat, Message
import logging
import atexit

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("deltachat_bot")

# --- Configuraciones ---
BOT_EMAIL = "orrodriguez588@gmail.com"
BOT_PASSWORD = "cnkpjyridpqcbclu"
DC_ACCOUNT_PATH = "/tmp/dc_bot_account"
PORT = 10000

# Inicializamos Flask
app = Flask(__name__)

# Inicializamos la cuenta de DeltaChat
account = Account(db_path=DC_ACCOUNT_PATH)

# --- Cerrar cuenta al terminar ---
def shutdown_account():
    account.stop_io()
    account.shutdown()
    logger.info("Cuenta de DeltaChat cerrada")

atexit.register(shutdown_account)

# --- Configurar y conectar la cuenta ---
def setup_account():
    if not account.is_configured():
        logger.info("Configurando cuenta...")
        account.set_config("addr", BOT_EMAIL)
        account.set_config("mail_pw", BOT_PASSWORD)
        account.set_config("mail_server", "imap.gmail.com")
        account.set_config("mail_port", "993")
        account.set_config("mail_security", "SSL")
        account.set_config("send_server", "smtp.gmail.com")
        account.set_config("send_port", "465")
        account.set_config("send_security", "SSL")
        account.set_config("e2ee_enabled", "0")
        account.configure()

        timeout = 60
        start_time = time.time()
        while not account.is_configured() and time.time() - start_time < timeout:
            time.sleep(1)
            logger.info("Esperando configuración...")
        if not account.is_configured():
            raise RuntimeError("No se pudo configurar la cuenta")
    logger.info("Cuenta conectada correctamente")
    account.start_io()

# --- Subir archivo a uguu ---
def subir_a_uguu(file_path):
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 100:
            return None, f"El archivo es demasiado grande ({file_size_mb:.2f} MB). Máximo 100 MB."

        with open(file_path, "rb") as f:
            r = requests.post("https://uguu.se/upload.php", files={"files[]": f})
            if r.ok:
                url = r.json()["files"][0]["url"]
                logger.info(f"Archivo subido: {url}")
                return url, None
            else:
                return None, "Error al subir el archivo"
    except Exception as e:
        logger.error(f"Error al subir archivo: {e}")
        return None, "Ocurrió un error al subir el archivo"

# --- Procesar mensajes ---
def handle_messages():
    try:
        while True:
            for msg in account.get_all_messages():
                if not msg.is_seen():
                    chat = Chat(account, msg.chat_id)
                    contact = msg.get_sender_contact()
                    name = contact.display_name or contact.addr or "Usuario"

                    # Texto
                    if msg.text:
                        text = msg.text.strip().lower()
                        if text == "/start":
                            chat.send_text(f"¡Hola {name}! Envíame un archivo y te daré un enlace para descargarlo.")
                        elif text == "/help":
                            chat.send_text("Comandos:\n/start - Inicia\n/help - Ayuda\nEnvía un archivo para subirlo.")
                        else:
                            chat.send_text(f"No entendí el mensaje, {name}. Usa /help para ver comandos.")

                    # Archivos
                    file_path = msg.get_file()
                    if file_path and os.path.exists(file_path):
                        chat.send_text("Subiendo tu archivo...")
                        link, error = subir_a_uguu(file_path)
                        if link:
                            chat.send_text(f"Aquí está tu archivo:\n{link}")
                        else:
                            chat.send_text(f"No se pudo subir tu archivo: {error}")

                    msg.mark_seen()
            time.sleep(2)
    except Exception as e:
        logger.error(f"Error procesando mensajes: {e}")

# --- Iniciar hilo de procesamiento ---
def start_bot():
    setup_account()
    threading.Thread(target=handle_messages, daemon=True).start()

# --- Rutas Flask ---
@app.route("/")
def index():
    return "<h1>Bot de DeltaChat corriendo!</h1>"

# --- Inicio ---
if __name__ == "__main__":
    os.makedirs(os.path.dirname(DC_ACCOUNT_PATH), exist_ok=True)
    start_bot()
    logger.info(f"Servidor Flask corriendo en puerto {PORT}")
    app.run(host="0.0.0.0", port=PORT)