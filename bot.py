import os
import tempfile
import subprocess
import threading
import time
from flask import Flask
from deltachat import Account, account_hookimpl

app = Flask(__name__)

# Configuración ArcaneChat
DELTA_EMAIL = "multidown@arcanechat.me"
DELTA_PASSWORD = "mO*061119"
IMAP_SERVER = "arcanechat.me"  # O usa mail.arcanechat.me si es diferente
SMTP_SERVER = "arcanechat.me"
IMAP_PORT = "143"  # Puerto IMAP sin SSL
SMTP_PORT = "25"   # Puerto SMTP sin SSL
DB_PATH = os.path.join(os.getcwd(), "delta_chat.db")

class YoutubeDLBot:
    @account_hookimpl
    def ac_incoming_message(self, message):
        if any(domain in message.text.lower() for domain in ["youtube.com", "youtu.be"]):
            self._process_video_request(message)

    def _process_video_request(self, message):
        try:
            message.chat.send_text("🔄 Descargando tu video...")
            
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
    # 1. Configuración inicial
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    account = Account(DB_PATH)
    
    # 2. Configuración del servidor (STARTTLS)
    account.set_config("addr", DELTA_EMAIL)
    account.set_config("mail_pw", DELTA_PASSWORD)
    account.set_config("mail_server", IMAP_SERVER)
    account.set_config("mail_port", IMAP_PORT)
    account.set_config("send_server", SMTP_SERVER)
    account.set_config("send_port", SMTP_PORT)
    account.set_config("mail_security", "starttls")  # Usar STARTTLS
    account.set_config("send_security", "starttls")
    
    # 3. Configuración adicional
    account.set_config("e2ee_enabled", "1")
    account.set_config("server_flags", "2")  # Auto-detectar configuración
    
    # 4. Inicialización
    if not account.is_configured():
        print("Configurando cuenta por primera vez...")
        account.configure()
        time.sleep(20)  # Espera para sincronización inicial
    
    bot = YoutubeDLBot()
    account.add_account_plugin(bot)
    
    print(f"Bot iniciado para {DELTA_EMAIL}")
    print(f"IMAP: {IMAP_SERVER}:{IMAP_PORT}")
    print(f"SMTP: {SMTP_SERVER}:{SMTP_PORT}")
    return account

@app.route('/')
def health_check():
    return "Bot DeltaChat Operativo"

if __name__ == "__main__":
    from waitress import serve
    
    # Iniciar bot
    delta_account = setup_bot()
    
    # Iniciar servidor web para Render
    port = int(os.environ.get("PORT", 10000))
    serve_thread = threading.Thread(
        target=serve,
        args=(app,),
        kwargs={"host": "0.0.0.0", "port": port},
        daemon=True
    )
    serve_thread.start()
    
    # Mantener el bot activo
    try:
        while delta_account.is_configured():
            time.sleep(10)
    except KeyboardInterrupt:
        delta_account.shutdown()