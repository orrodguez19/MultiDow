import os
import tempfile
import subprocess
import threading
import time
from flask import Flask
from deltachat import Account, account_hookimpl

app = Flask(__name__)

# Configuración DeltaChat (¡Actualiza estos valores!)
DELTA_EMAIL = "multidown@arcanechat.me"
DELTA_PASSWORD = "mO*061119"
IMAP_SERVER = "mail.arcanechat.me"
SMTP_SERVER = "mail.arcanechat.me"
DB_PATH = os.path.join(os.getcwd(), "delta_chat.db")

class YoutubeDLBot:
    @account_hookimpl
    def ac_incoming_message(self, message):
        """Procesa mensajes entrantes con soporte E2EE"""
        if message.is_encrypted():
            print(f"Mensaje cifrado recibido de {message.get_sender_contact().addr}")
            
            if any(domain in message.text.lower() for domain in ["youtube.com", "youtu.be"]):
                self._process_video_request(message)
        else:
            message.chat.send_text("🔒 Por favor inicia un chat cifrado conmigo primero")

    def _process_video_request(self, message):
        try:
            message.chat.send_text("🔄 Descargando tu video... (esto puede tomar unos minutos)")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                video_path = f"{tmpdir}/video.mp4"
                subprocess.run([
                    "yt-dlp",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                    "--merge-output-format", "mp4",
                    "-o", video_path,
                    message.text.strip()
                ], check=True, timeout=300)
                
                if os.path.exists(video_path):
                    message.chat.send_video(video_path)
                    print(f"Video enviado a {message.get_sender_contact().addr}")
                else:
                    message.chat.send_text("❌ No se pudo descargar el video")
        except Exception as e:
            message.chat.send_text(f"❌ Error: {str(e)}")
            app.logger.error(f"Error procesando video: {e}")

def setup_bot():
    """Configuración completa del bot con soporte E2EE"""
    # 1. Inicialización de cuenta
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    account = Account(DB_PATH)
    
    # 2. Configuración IMAP/SMTP
    account.set_config("addr", DELTA_EMAIL)
    account.set_config("mail_pw", DELTA_PASSWORD)
    account.set_config("mail_server", IMAP_SERVER)
    account.set_config("mail_port", "143")
    account.set_config("send_server", SMTP_SERVER)
    account.set_config("send_port", "25")
    account.set_config("mail_security", "ssl")
    
    # 3. Configuración PGP para E2EE
    account.set_config("save_keys", "1")
    account.set_config("autocrypt_prefer_encrypt", "mutual")
    
    # 4. Inicialización
    if not account.is_configured():
        print("Configurando cuenta por primera vez...")
        account.configure()
        time.sleep(30)  # Espera inicial para sincronización
    
    # 5. Verificación de contacto
    bot = YoutubeDLBot()
    account.add_account_plugin(bot)
    
    print(f"Bot iniciado correctamente. Cuenta: {DELTA_EMAIL}")
    print(f"Clave pública PGP:\n{account.get_config('public_key')}")
    
    return account

@app.route('/')
def health_check():
    return "Bot DeltaChat Operativo"

if __name__ == "__main__":
    # Iniciar en modo producción
    from waitress import serve
    
    # 1. Iniciar bot DeltaChat
    delta_account = setup_bot()
    
    # 2. Iniciar servidor web
    port = int(os.environ.get("PORT", 10000))
    serve_thread = threading.Thread(
        target=serve,
        args=(app,),
        kwargs={"host": "0.0.0.0", "port": port},
        daemon=True
    )
    serve_thread.start()
    
    # 3. Mantener bot activo
    try:
        while True:
            time.sleep(10)
            print("Estado:", "OK" if delta_account.is_configured() else "ERROR")
    except KeyboardInterrupt:
        delta_account.shutdown()