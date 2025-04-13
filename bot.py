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
logger.info(f"Intentando usar DC_ACCOUNT_PATH: {DC_ACCOUNT_PATH}")
logger.info(f"Directorio padre existe: {os.path.exists(os.path.dirname(DC_ACCOUNT_PATH))}")
logger.info(f"Directorio padre escribible: {os.access(os.path.dirname(DC_ACCOUNT_PATH), os.W_OK)}")
account = Account(db_path=DC_ACCOUNT_PATH)

# --- Cerrar cuenta al terminar ---
def shutdown_account():
    if account.is_running():
        account.stop_io()
        account.shutdown()
        logger.info("Cuenta de DeltaChat cerrada")

atexit.register(shutdown_account)

# --- Configurar y conectar la cuenta ---
def setup_account():
    try:
        if not account.is_configured():
            logger.info("Configurando cuenta de DeltaChat...")
            # Establecer configuración usando set_config
            account.set_config("addr", BOT_EMAIL)
            account.set_config("mail_pw", BOT_PASSWORD)
            account.set_config("mail_server", "imap.gmail.com")
            account.set_config("mail_port", "993")
            account.set_config("mail_security", "SSL")
            account.set_config("send_server", "smtp.gmail.com")
            account.set_config("send_port", "465")
            account.set_config("send_security", "SSL")
            account.set_config("e2ee_enabled", "0")  # Sin cifrado de extremo a extremo
            
            # Configurar la cuenta
            account.configure()
            
            # Esperar a que la configuración se complete
            timeout = 60
            start_time = time.time()
            while not account.is_configured() and time.time() - start_time < timeout:
                time.sleep(1)
                logger.info("Esperando configuración...")
            if not account.is_configured():
                logger.error("No se pudo configurar la cuenta de DeltaChat")
                raise RuntimeError("No se pudo configurar la cuenta de DeltaChat")
            logger.info("Cuenta configurada correctamente")
        if not account.is_running():
            account.start_io()
            logger.info("Conexión de DeltaChat iniciada")
    except Exception as e:
        logger.error(f"Error en setup_account: {e}")
        raise

# --- Función para subir archivos a uguu ---
def subir_a_uguu(file_path):
    max_size_mb = 100
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            logger.warning(f"Archivo demasiado grande: {file_size_mb} MB")
            return None
        with open(file_path, "rb") as f:
            r = requests.post("https://uguu.se/upload.php", files={"files[]": f})
            if r.ok:
                url = r.json()["files"][0]["url"]
                logger.info(f"Archivo subido: {url}")
                return url
    except Exception as e:
        logger.error(f"Error al subir archivo: {e}")
    return None

# --- Procesar mensajes nuevos ---
def process_messages():
    try:
        setup_account()
        while True:
            event = account.wait_for_event()
            if event.kind == "DC_EVENT_INCOMING_MSG":
                chat_id = event.chat_id
                msg_id = event.msg_id
                msg = account.get_message_by_id(msg_id)
                if msg.is_in_fresh() or msg.is_in_noticed():
                    if msg.file and os.path.exists(msg.file):
                        logger.info(f"Procesando archivo: {msg.file}")
                        link = subir_a_uguu(msg.file)
                        if link:
                            chat = Chat(account, chat_id)
                            chat.send_text(f"Aquí está tu enlace de descarga: {link}")
                            logger.info(f"Enlace enviado: {link}")
                        else:
                            logger.warning("No se pudo subir el archivo")
                        msg.mark_seen()
    except Exception as e:
        logger.error(f"Error en process_messages: {e}")
        raise

# --- Iniciar el procesamiento de mensajes en un hilo separado ---
def start_message_processing():
    threading.Thread(target=process_messages, daemon=True).start()

# --- Ruta principal del sitio ---
@app.route("/")
def index():
    return render_template("index.html")

# --- Inicio del servidor ---
if __name__ == "__main__":
    try:
        os.makedirs(os.path.dirname(DC_ACCOUNT_PATH), exist_ok=True)
        start_message_processing()
        logger.info(f"Iniciando servidor Flask en puerto {PORT}")
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {e}")
        raise