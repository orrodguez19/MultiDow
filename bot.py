import os
import re
import smtplib
import time
import subprocess
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from dotenv import load_dotenv
import ssl
from imap_tools import MailBox, AND
from datetime import datetime, timedelta
from flask import Flask
import threading
from deltachat import account_hookimpl, run_cmdline, Account

# Configuración de Flask
app = Flask(__name__)

# Configuración Nauta.cu
load_dotenv()
EMAIL_USER = os.getenv('EMAIL_USER', 'miguelorlandos@nauta.cu')
EMAIL_PASS = os.getenv('EMAIL_PASS', 'TdrPQQxq')
IMAP_SERVER = 'imap.nauta.cu'
IMAP_PORT = 143
SMTP_SERVER = 'smtp.nauta.cu'
SMTP_PORT = 25

# Configuración DeltaChat
DELTA_CHAT_EMAIL = os.getenv('DELTA_CHAT_EMAIL')
DELTA_CHAT_PASS = os.getenv('DELTA_CHAT_PASS')

# Ajustes optimizados
SSL_VERIFY = False
TIMEOUT = 10
CHECK_INTERVAL = 10  # 5 minutos

class NautaDeltaBot:
    def __init__(self):
        self.delta_account = None
        self.init_delta_chat()
    
    def init_delta_chat(self):
        """Inicializa la cuenta de DeltaChat"""
        if DELTA_CHAT_EMAIL and DELTA_CHAT_PASS:
            self.delta_account = Account()
            self.delta_account.set_config("addr", DELTA_CHAT_EMAIL)
            self.delta_account.set_config("mail_pw", DELTA_CHAT_PASS)
            self.delta_account.start_io()

    @account_hookimpl
    def ac_incoming_message(self, message):
        """Maneja mensajes entrantes de DeltaChat"""
        try:
            if "instagram.com" in message.text:
                self.handle_instagram(message)
            elif "youtube.com" in message.text:
                self.handle_youtube(message)
            elif message.text.strip().lower() == "status":
                self.send_status(message.chat)
        except Exception as e:
            print(f"[DELTA] Error procesando mensaje: {e}")

    def handle_instagram(self, message):
        """Procesa enlaces de Instagram"""
        message.chat.send_text("📩 Instagram link recibido. Procesando...")
        # Aquí puedes añadir lógica para procesar Instagram
        
    def handle_youtube(self, message):
        """Descarga videos de YouTube"""
        urls = re.findall(r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)', message.text)
        for url in urls:
            video_path = self.download_video(url)
            if video_path:
                message.chat.send_text(f"🎥 Video descargado: {os.path.basename(video_path)}")
                message.chat.send_file(video_path)
                os.remove(video_path)  # Limpiar después de enviar

    def send_status(self, chat):
        """Envía estado del sistema"""
        status_msg = (
            f"🟢 Bot operativo\n"
            f"📧 Nauta: {EMAIL_USER}\n"
            f"🕒 Última verificación: {datetime.now()}\n"
            f"📊 Correos procesados: {self.get_processed_count()}"
        )
        chat.send_text(status_msg)

    def download_video(self, url):
        """Descarga videos de YouTube"""
        try:
            download_dir = "youtube_downloads"
            os.makedirs(download_dir, exist_ok=True)
            
            cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]',
                '--no-playlist',
                '--restrict-filenames',
                '-o', f'{download_dir}/%(title)s.%(ext)s',
                url
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Buscar el archivo descargado
            files = os.listdir(download_dir)
            if files:
                return os.path.join(download_dir, files[-1])
            return None
        except Exception as e:
            print(f"[YT-DLP] Error: {e}")
            return None

    def get_processed_count(self):
        """Obtiene conteo de correos procesados"""
        # Implementar lógica de conteo según tu necesidad
        return 0

# Flask endpoints (para Render)
@app.route('/')
def health_check():
    return f"Bot Nauta/DeltaChat activo | {datetime.now()}", 200

@app.route('/status')
def status():
    return {
        "status": "operational",
        "services": {
            "nauta": f"{EMAIL_USER}",
            "deltachat": "active" if DELTA_CHAT_EMAIL else "inactive"
        },
        "timestamp": datetime.now().isoformat()
    }

def run_flask_server():
    """Inicia servidor web para Render"""
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def main():
    """Punto de entrada principal"""
    bot = NautaDeltaBot()
    
    # Hilo para Flask (Render)
    web_thread = threading.Thread(target=run_flask_server, daemon=True)
    web_thread.start()
    
    # Hilo para DeltaChat
    if DELTA_CHAT_EMAIL and DELTA_CHAT_PASS:
        delta_thread = threading.Thread(
            target=run_cmdline,
            kwargs={"account_plugins": [bot]},
            daemon=True
        )
        delta_thread.start()
    
    # Bucle principal para Nauta
    while True:
        try:
            print(f"\n[{datetime.now()}] Verificando correos Nauta...")
            # Aquí iría tu lógica de check_emails()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()