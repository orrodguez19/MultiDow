import os
import tempfile
import subprocess
import threading
from flask import Flask
from deltachat import Account, account_hookimpl

app = Flask(__name__)

# Configuración
DELTA_EMAIL = "multidown@arcanechat.me"
DELTA_PASSWORD = "mO*061119"
IMAP_SERVER = "mail.arcanechat.me"
IMAP_PORT = "143"
SMTP_SERVER = "mail.arcanechat.me"
SMTP_PORT = "25"
DB_PATH = os.path.join(os.getcwd(), "delta_chat.db")

class YoutubeDLBot:
    @account_hookimpl
    def ac_incoming_message(self, message):
        if any(domain in message.text.lower() for domain in ["youtube.com", "youtu.be", "tiktok.com"]):
            message.chat.send_text("🔄 Procesando tu video...")
            threading.Thread(
                target=self._download_video,
                args=(message,),
                daemon=True
            ).start()

    def _download_video(self, message):
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
            message.chat.send_text(f"❌ Error: {str(e)}")

def setup_bot():
    account = Account(DB_PATH)
    account.set_config("addr", DELTA_EMAIL)
    account.set_config("mail_pw", DELTA_PASSWORD)
    account.set_config("mail_server", IMAP_SERVER)
    account.set_config("mail_port", IMAP_PORT)
    account.set_config("send_server", SMTP_SERVER)
    account.set_config("send_port", SMTP_PORT)
    account.set_config("mail_security", "ssl")
    
    if not account.is_configured():
        account.configure()
    
    bot = YoutubeDLBot()
    account.add_account_plugin(bot)
    return account

@app.route('/')
def health_check():
    return "Bot activo"

if __name__ == "__main__":
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Iniciar bot
    account = setup_bot()
    
    # Iniciar Flask en segundo plano
    port = int(os.environ.get("PORT", 10000))
    flask_thread = threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": port},
        daemon=True
    )
    flask_thread.start()
    
    # Mantener el bot activo (forma correcta)
    print("Bot DeltaChat iniciado")
    account.wait_shutdown()  # Reemplazo correcto para run()