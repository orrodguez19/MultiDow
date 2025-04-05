import os
import tempfile
import subprocess
import threading
from flask import Flask
from deltachat import Account, account_hookimpl

app = Flask(__name__)

## CONFIGURACIÓN DIRECTA (EDITA ESTOS VALORES) ##
DELTA_EMAIL = "multidown@arcanechat.me"
DELTA_PASSWORD = "mO*061119"
IMAP_SERVER = "mail.arcanechat.me"
IMAP_PORT = "143"
SMTP_SERVER = "mail.arcanechat.me"
SMTP_PORT = "25"
###############################################

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
                    "--no-playlist",
                    message.text.strip()
                ], check=True, timeout=300)
                
                if os.path.exists(video_path):
                    if os.path.getsize(video_path) > 25 * 1024 * 1024:  # 25MB
                        message.chat.send_text("⚠️ Video demasiado grande (límite: 25MB)")
                    else:
                        message.chat.send_video(video_path)
                else:
                    message.chat.send_text("❌ Error al descargar el video")
        except subprocess.TimeoutExpired:
            message.chat.send_text("⏳ Tiempo excedido - Intenta con un video más corto")
        except Exception as e:
            message.chat.send_text(f"❌ Error: {str(e)}")

def setup_bot():
    account = Account()
    account.set_config("addr", DELTA_EMAIL)
    account.set_config("mail_pw", DELTA_PASSWORD)
    account.set_config("mail_server", IMAP_SERVER)
    account.set_config("mail_port", IMAP_PORT)
    account.set_config("send_server", SMTP_SERVER)
    account.set_config("send_port", SMTP_PORT)
    account.set_config("mail_security", "ssl")
    
    account.configure()
    bot = YoutubeDLBot()
    account.add_account_plugin(bot)
    return account

@app.route('/')
def health_check():
    return "Bot DeltaChat activo"

if __name__ == "__main__":
    delta_bot = setup_bot()
    
    # Iniciar Flask en puerto para Render
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": port},
        daemon=True
    ).start()
    
    # Mantener el bot activo
    delta_bot.run()