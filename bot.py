import os
import tempfile
import subprocess
import threading
import time
from flask import Flask, Response
from deltachat import Account, account_hookimpl

app = Flask(__name__)

# Configuración - RELLENA ESTOS VALORES
DELTA_EMAIL = "multidown@arcanechat.me"
DELTA_PASSWORD = "mO*061119"
IMAP_SERVER = "arcanechat.me"
SMTP_SERVER = "arcanechat.me"
DB_PATH = "/tmp/delta_chat.db"  # Usar /tmp en Render

class YoutubeDLBot:
    @account_hookimpl
    def ac_incoming_message(self, message):
        if any(domain in message.text.lower() for domain in ["youtube.com", "youtu.be"]):
            self._process_video(message)

    def _process_video(self, message):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                video_path = f"{tmpdir}/video.mp4"
                subprocess.run([
                    "yt-dlp",
                    "-f", "best[ext=mp4]",
                    "-o", video_path,
                    message.text.strip()
                ], check=True, timeout=300)
                
                if os.path.exists(video_path):
                    message.chat.send_video(video_path)
        except Exception as e:
            message.chat.send_text(f"Error: {str(e)}")

def setup_bot():
    account = Account(DB_PATH)
    # Configuración IMAP/SMTP
    account.set_config("addr", DELTA_EMAIL)
    account.set_config("mail_pw", DELTA_PASSWORD)
    account.set_config("mail_server", IMAP_SERVER)
    account.set_config("mail_port", "143")
    account.set_config("send_server", SMTP_SERVER)
    account.set_config("send_port", "25")
    account.set_config("mail_security", "ssl")
    
    if not account.is_configured():
        account.configure()
        time.sleep(15)
    
    return account

@app.route('/')
def health_check():
    """Endpoint de health check obligatorio para Render"""
    return Response("Bot DeltaChat Operativo", status=200, mimetype='text/plain')

def run_web_server():
    """Inicia el servidor web en el puerto correcto"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

if __name__ == "__main__":
    # 1. Configuración inicial
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 2. Iniciar bot DeltaChat en segundo plano
    bot_account = setup_bot()
    bot_thread = threading.Thread(
        target=bot_account.run_forever,
        daemon=True
    )
    bot_thread.start()
    
    # 3. Iniciar servidor web (OBLIGATORIO para Render)
    run_web_server()