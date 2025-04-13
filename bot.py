import os
import threading
import time
from flask import Flask, render_template
import requests
from deltachat import Account, Chat
import logging
import atexit

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deltachat_bot")

BOT_EMAIL = "orrodriguez588@gmail.com"
BOT_PASSWORD = "cnkpjyridpqcbclu"
DC_ACCOUNT_PATH = "/tmp/dc_bot_account"
PORT = 10000

app = Flask(__name__)
account = Account(db_path=DC_ACCOUNT_PATH)

def shutdown_account():
    account.stop_io()
    account.shutdown()
    logger.info("Cuenta cerrada")
atexit.register(shutdown_account)

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
        time.sleep(5)

    timeout = time.time() + 60
    while not account.is_configured() and time.time() < timeout:
        logger.info("Esperando configuración...")
        time.sleep(1)

    if not account.is_configured():
        raise RuntimeError("No se pudo configurar la cuenta")

    account.start_io()
    logger.info("Cuenta conectada correctamente")

def subir_a_uguu(file_path):
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 100:
            return None, "Archivo demasiado grande (máx. 100MB)"
        with open(file_path, "rb") as f:
            r = requests.post("https://uguu.se/upload.php", files={"files[]": f})
            if r.ok:
                return r.json()["files"][0]["url"], None
    except Exception as e:
        logger.error(f"Error al subir archivo: {e}")
        return None, "Error al subir archivo"
    return None, "No se pudo subir el archivo"

def process_incoming():
    while True:
        try:
            msglist = account.get_messages()
            for msg in msglist:
                if not msg.is_seen():
                    chat = msg.chat
                    contact = msg.get_sender_contact()
                    name = contact.display_name or contact.addr or "Usuario"

                    if msg.text:
                        txt = msg.text.strip().lower()
                        if txt == "/start":
                            chat.send_text(f"¡Hola, {name}! Envíame un archivo y te daré un enlace.")
                        elif txt == "/help":
                            chat.send_text("Usa /start para comenzar. Envíame un archivo (máx 100MB).")
                        else:
                            chat.send_text(f"No entendí eso, {name}. Usa /help para ayuda.")

                    if msg.file and os.path.exists(msg.file):
                        chat.send_text(f"Recibido, {name}. Subiendo...")
                        link, err = subir_a_uguu(msg.file)
                        if link:
                            chat.send_text(f"¡Listo! Aquí tienes tu enlace:\n{link}")
                        else:
                            chat.send_text(f"Error: {err}")
                    msg.mark_seen()
        except Exception as e:
            logger.error(f"Error procesando mensajes: {e}")
        time.sleep(5)

def start_bot():
    setup_account()
    threading.Thread(target=process_incoming, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    os.makedirs(os.path.dirname(DC_ACCOUNT_PATH), exist_ok=True)
    start_bot()
    app.run(host="0.0.0.0", port=PORT)