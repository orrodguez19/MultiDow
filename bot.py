import os
import threading
import time
from flask import Flask, render_template
import requests
from deltachat import Account, Chat, Message, EventLogger

# --- Configuraciones ---
BOT_EMAIL = "multidown@arcanechat.me"
BOT_PASSWORD = "mO*061119"
DC_ACCOUNT_PATH = "/tmp/dc_bot_account"
PORT = 10000

# Inicializamos Flask
app = Flask(__name__)

# Inicializamos la cuenta de DeltaChat con un logger para depuración
account = Account(db_path=DC_ACCOUNT_PATH)
logger = EventLogger(account, "deltachat_bot", level="INFO")

# --- Configurar y conectar la cuenta ---
def setup_account():
    if not account.is_configured():
        print("Configurando cuenta de DeltaChat...")
        account.configure(
            addr=BOT_EMAIL,
            mail_pw=BOT_PASSWORD,
            provider="",
            server_flags=0,
            e2ee_enabled=True,
        )
        account.start_io()
        # Esperar a que la configuración se complete
        timeout = 60  # segundos
        start_time = time.time()
        while not account.is_configured() and time.time() - start_time < timeout:
            time.sleep(1)
        if not account.is_configured():
            raise RuntimeError("No se pudo configurar la cuenta de DeltaChat")
        print("Cuenta configurada correctamente")
    if not account.is_running():
        account.start_io()
        print("Conexión de DeltaChat iniciada")

# --- Función para subir archivos a uguu ---
def subir_a_uguu(file_path):
    try:
        with open(file_path, "rb") as f:
            r = requests.post("https://uguu.se/upload.php", files={"files[]": f})
            if r.ok:
                return r.json()["files"][0]["url"]
    except Exception as e:
        print(f"Error al subir archivo: {e}")
    return None

# --- Procesar mensajes nuevos en tiempo real ---
def process_messages():
    setup_account()
    while True:
        event = account.wait_for_event()
        if event.kind == "DC_EVENT_INCOMING_MSG":
            chat_id = event.chat_id
            msg_id = event.msg_id
            msg = account.get_message_by_id(msg_id)
            if msg.is_in_fresh() or msg.is_in_noticed():  # Mensaje no leído
                if msg.file and os.path.exists(msg.file):
                    print(f"Procesando archivo: {msg.file}")
                    link = subir_a_uguu(msg.file)
                    if link:
                        chat = Chat(account, chat_id)
                        chat.send_text(f"Aquí está tu enlace de descarga: {link}")
                        print(f"Enlace enviado: {link}")
                    msg.mark_seen()

# --- Iniciar el procesamiento de mensajes en un hilo separado ---
def start_message_processing():
    threading.Thread(target=process_messages, daemon=True).start()

# --- Comando para crear el enlace de invitación ---
def crear_enlace_invitacion():
    setup_account()
    try:
        qr_code = account.get_qr_code()
        return f"https://web.deltachat-mailbox.org/#/chat?dcqr={qr_code}"
    except Exception as e:
        print(f"Error al generar QR: {e}")
        return "#"

# --- Ruta principal del sitio ---
@app.route("/")
def index():
    enlace = crear_enlace_invitacion()
    return render_template("index.html", enlace=enlace)

# --- Inicio del servidor ---
if __name__ == "__main__":
    os.makedirs(os.path.dirname(DC_ACCOUNT_PATH), exist_ok=True)
    # Iniciar el procesamiento de mensajes
    start_message_processing()
    port = int(os.environ.get("PORT", PORT))  # Compatible con Render
    app.run(host="0.0.0.0", port=port)