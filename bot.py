import os
import subprocess
from flask import Flask, render_template
from flask import request
import requests

# --- Configuraciones ---
BOT_EMAIL = "multidown@arcanechat.me"
BOT_PASSWORD = "mO*061119"
DC_CLI_PATH = "/ruta/a/deltachat"
DC_ACCOUNT_PATH = "/tmp/dc_bot_account"
PORT = 10000

# Inicializamos Flask
app = Flask(__name__)

# --- Comando para crear el enlace de invitación ---
def crear_enlace_invitacion():
    cmd = [
        DC_CLI_PATH,
        "--db", DC_ACCOUNT_PATH,
        "qr",
        "create",
        "--contact",
        f"{BOT_EMAIL};password={BOT_PASSWORD}"
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    for line in resultado.stdout.splitlines():
        if line.startswith("dcqr:"):
            return f"https://web.deltachat-mailbox.org/#/chat?dcqr={line[5:]}"
    return "#"

# --- Función para subir archivos a uguu ---
def subir_a_uguu(file_path):
    with open(file_path, "rb") as f:
        r = requests.post("https://uguu.se/upload.php", files={"files[]": f})
        if r.ok:
            return r.json()["files"][0]["url"]
    return None

# --- Verificar mensajes nuevos en DeltaChat ---
def revisar_mensajes():
    cmd = [DC_CLI_PATH, "--db", DC_ACCOUNT_PATH, "msgs", "list", "--unseen"]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    mensajes = resultado.stdout.strip().split("\n\n")
    for mensaje in mensajes:
        if "file:" in mensaje:
            partes = mensaje.split("\n")
            file_line = next((l for l in partes if l.startswith("file:")), None)
            chat_id_line = next((l for l in partes if l.startswith("chat_id:")), None)
            if file_line and chat_id_line:
                file_path = file_line.replace("file: ", "").strip()
                chat_id = chat_id_line.replace("chat_id: ", "").strip()
                link = subir_a_uguu(file_path)
                if link:
                    subprocess.run([
                        DC_CLI_PATH,
                        "--db", DC_ACCOUNT_PATH,
                        "chats", "send-text",
                        "--chat", chat_id,
                        "--text", f"Aquí está tu enlace de descarga: {link}"
                    ])

# --- Ruta principal del sitio ---
@app.route("/")
def index():
    enlace = crear_enlace_invitacion()
    return render_template("index.html", enlace=enlace)

# --- Ruta webhook para revisar mensajes (puedes usar un cron también) ---
@app.route("/webhook", methods=["POST"])
def webhook():
    revisar_mensajes()
    return "OK"

# --- Inicio del servidor ---
if __name__ == "__main__":
    os.makedirs(os.path.dirname(DC_ACCOUNT_PATH), exist_ok=True)
    # Crear cuenta si no existe
    if not os.path.exists(DC_ACCOUNT_PATH):
        subprocess.run([
            DC_CLI_PATH,
            "--db", DC_ACCOUNT_PATH,
            "account", "setup",
            "--addr", BOT_EMAIL,
            "--mail_pw", BOT_PASSWORD
        ])
    app.run(host="0.0.0.0", port=PORT)