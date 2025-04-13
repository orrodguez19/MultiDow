import os
import time
import logging
import requests
from flask import Flask
from deltachat_rpc_client import Account

# DATOS DEL BOT — MODIFÍCALOS AQUÍ
BOT_EMAIL = "orrodriguez588@gmail.com"
BOT_PASSWORD = "cnkpjyridpqcbclu"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("deltachat_bot")

app = Flask(__name__)
account = None

@app.route("/", methods=["GET", "HEAD"])
def home():
    return "Bot activo"

def handle_msg(chat_id, msg_id):
    msg = account.get_message(msg_id)
    if msg["file"]:
        logger.info("Archivo recibido, subiendo a uguu...")
        file_path = msg["file"]
        with open(file_path, "rb") as f:
            res = requests.post("https://uguu.se/upload.php", files={"file": f})
        if res.status_code == 200:
            url = res.json()["files"][0]["url"]
            logger.info(f"Archivo subido: {url}")
            account.send_text(chat_id, f"Aquí está tu archivo: {url}")
        else:
            account.send_text(chat_id, "Hubo un error al subir el archivo.")
    else:
        account.send_text(chat_id, "Envíame un archivo para subirlo a Uguu.")

def main():
    global account
    logger.info("Configurando cuenta...")

    os.makedirs("bot_data", exist_ok=True)
    account = Account("bot_data")
    if not account.is_configured():
        account.set_config("mail_smtp_server", "smtp.gmail.com")
        account.set_config("mail_smtp_port", "587")
        account.set_config("mail_imap_server", "imap.gmail.com")
        account.set_config("mail_imap_port", "993")
        account.set_config("mail_user", BOT_EMAIL)
        account.set_config("mail_password", BOT_PASSWORD)
        account.set_config("displayname", "Bot de Uguu")
        account.configure()
        logger.info("Cuenta configurada correctamente")
    else:
        logger.info("Cuenta ya configurada")

    account.start_io()
    logger.info("Escuchando mensajes...")

    def on_event(event):
        if event["type"] == "msg":
            handle_msg(event["chat_id"], event["msg_id"])

    account.set_event_handler(on_event)

    # Iniciar Flask en segundo plano
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        account.stop_io()

if __name__ == "__main__":
    main()