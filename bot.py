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
        logging.FileHandler("bot.log"),  # Guarda logs en un archivo
        logging.StreamHandler()          # Muestra logs en consola
    ]
)
logger = logging.getLogger("deltachat_bot")

# --- Configuraciones ---
BOT_EMAIL = os.environ.get("BOT_EMAIL", "bot@example.com")  # Usa variable de entorno
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "tu_contraseña")
DC_ACCOUNT_PATH = os.environ.get("DC_ACCOUNT_PATH", "/tmp/dc_bot_account")  # Ruta temporal para pruebas
PORT = int(os.environ.get("PORT", 10000))

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
            account.configure(
                addr=BOT_EMAIL,
                mail_pw=BOT_PASSWORD,
                provider="",
                server_flags=0,
                e2ee_enabled=True,
            )
            account.start_io()
            timeout = 60  # segundos
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
    max_size_mb = 100  # Límite de uguu.se
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

# --- Procesar mensajes nuevos en tiempo real ---
def process_messages():
    try:
        setup_account()
        while True:
            event = account.wait_for_event()
            if event.kind == "DC_EVENT_INCOMING_MSG":
                chat_id = event.chat_id
                msg_id = event.msg_id
                msg = account.get_message_by_id(msg_id)
                if msg.is_in_fresh() or msg.is_in_noticed():  # Mensaje no leído
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

# --- Comando para crear el enlace de invitación ---
def crear_enlace_invitacion():
    try:
        setup_account()
        qr_code = account.get_qr_code()
        enlace = f"https://web.deltachat-mailbox.org/#/chat?dcqr={qr_code}"
        logger.info(f"Enlace de invitación generado: {enlace}")
        return enlace
    except Exception as e:
        logger.error(f"Error al generar QR: {e}")
        return "#"

# --- Ruta principal del sitio ---
@app.route("/")
def index():
    enlace = crear_enlace_invitacion()
    return render_template("index.html", enlace=enlace)

# --- Inicio del servidor ---
if __name__ == "__main__":
    try:
        os.makedirs(os.path.dirname(DC_ACCOUNT_PATH), exist_ok=True)
        # Iniciar el procesamiento de mensajes
        start_message_processing()
        logger.info(f"Iniciando servidor Flask en puerto {PORT}")
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {e}")
        raise