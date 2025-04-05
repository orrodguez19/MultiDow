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

# Cargar variables de entorno
load_dotenv()

# Configuración Nauta.cu
EMAIL_USER = "miguelorlandos@nauta.cu"
EMAIL_PASS = "TdrPQQxq"
IMAP_SERVER = 'imap.nauta.cu'
IMAP_PORT = 143
SMTP_SERVER = 'smtp.nauta.cu'
SMTP_PORT = 25

# Configuración DeltaChat
DELTA_CHAT_EMAIL = "miguelorlandos@nauta.cu"
DELTA_CHAT_PASS = "TdrPQQxq"
IMAP_SERVER = 'imap.nauta.cu'
IMAP_PORT = 143
SMTP_SERVER = 'smtp.nauta.cu'
SMTP_PORT = 25

# Ajustes optimizados
SSL_VERIFY = False
TIMEOUT = 8
CHECK_INTERVAL = 8  # 5 minutos entre verificaciones

class NautaDeltaBot:
    def __init__(self):
        self.delta_account = None
        # Configuración de la base de datos para Render
        db_folder = os.path.join(os.getenv("TEMP", "/tmp"), "deltachat_data")
        os.makedirs(db_folder, exist_ok=True)
        self.db_path = os.path.join(db_folder, "account.db")
        self.init_delta_chat()
    
    def init_delta_chat(self):
        """Inicializa la cuenta de DeltaChat con manejo de errores"""
        if not all([DELTA_CHAT_EMAIL, DELTA_CHAT_PASS]):
            print("DeltaChat no configurado - faltan credenciales")
            return

        try:
            print(f"Inicializando DeltaChat con DB en: {self.db_path}")
            
            self.delta_account = Account(self.db_path)
            self.delta_account.set_config("addr", DELTA_CHAT_EMAIL)
            self.delta_account.set_config("mail_pw", DELTA_CHAT_PASS)
            
            # Configuraciones recomendadas para bots
            self.delta_account.set_config("bot", "1")
            self.delta_account.set_config("mvbox_move", "1")
            self.delta_account.set_config("e2ee_enabled", "0")
            
            self.delta_account.start_io()
            print(f"DeltaChat iniciado para {DELTA_CHAT_EMAIL}")
            
        except Exception as e:
            print(f"Error al iniciar DeltaChat: {str(e)}")
            self.delta_account = None

    @account_hookimpl
    def ac_incoming_message(self, message):
        """Maneja mensajes entrantes de DeltaChat"""
        try:
            print(f"Mensaje recibido de {message.from_} - {message.text[:50]}...")
            
            if "instagram.com" in message.text:
                self.handle_instagram(message)
            elif "youtube.com" in message.text:
                self.handle_youtube(message)
            elif message.text.strip().lower() == "status":
                self.send_status(message.chat)
            else:
                message.chat.send_text("🤖 Comando no reconocido. Prueba con 'status'")
                
        except Exception as e:
            print(f"Error procesando mensaje: {e}")
            message.chat.send_text("⚠️ Error procesando tu mensaje")

    def handle_instagram(self, message):
        """Procesa enlaces de Instagram"""
        message.chat.send_text("📸 Instagram link recibido. Procesando...")
        # Implementa aquí tu lógica para Instagram

    def handle_youtube(self, message):
        """Descarga y envía videos de YouTube"""
        message.chat.send_text("⏳ Descargando video de YouTube...")
        urls = re.findall(r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)', message.text)
        
        for url in urls:
            try:
                video_path = self.download_video(url)
                if video_path:
                    message.chat.send_text(f"✅ Video descargado: {os.path.basename(video_path)}")
                    message.chat.send_file(video_path)
                    os.remove(video_path)
                else:
                    message.chat.send_text("❌ No se pudo descargar el video")
            except Exception as e:
                message.chat.send_text(f"⚠️ Error: {str(e)}")

    def download_video(self, url):
        """Descarga videos de YouTube usando yt-dlp"""
        try:
            download_dir = os.path.join(os.getenv("TEMP", "/tmp"), "youtube_downloads")
            os.makedirs(download_dir, exist_ok=True)
            
            cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]',
                '--no-playlist',
                '--restrict-filenames',
                '-o', f'{download_dir}/%(title)s.%(ext)s',
                url
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Encontrar el archivo descargado más reciente
            files = sorted(
                [f for f in os.listdir(download_dir) if f.endswith(('.mp4', '.webm'))],
                key=lambda x: os.path.getmtime(os.path.join(download_dir, x)),
                reverse=True
            )
            
            return os.path.join(download_dir, files[0]) if files else None
            
        except subprocess.CalledProcessError as e:
            print(f"Error yt-dlp: {e.stderr}")
            return None
        except Exception as e:
            print(f"Error descargando video: {e}")
            return None

    def send_status(self, chat):
        """Envía el estado del sistema"""
        status_msg = (
            "🟢 Bot Operativo\n"
            f"📧 Nauta: {EMAIL_USER}\n"
            f"🔵 DeltaChat: {DELTA_CHAT_EMAIL or 'No configurado'}\n"
            f"🕒 Última verificación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        chat.send_text(status_msg)

# Endpoints Flask para Render
@app.route('/')
def health_check():
    return "🟢 Bot Nauta/DeltaChat Operativo", 200

@app.route('/status')
def status():
    return {
        "status": "operational",
        "nauta_account": EMAIL_USER,
        "delta_account": DELTA_CHAT_EMAIL or "not_configured",
        "last_check": datetime.now().isoformat()
    }

def run_flask_server():
    """Inicia el servidor web para Render"""
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def check_emails():
    """Verifica correos nuevos en Nauta"""
    try:
        ssl_context = ssl.create_default_context()
        if not SSL_VERIFY:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        with MailBox(IMAP_SERVER, port=IMAP_PORT) as mailbox:
            mailbox.starttls(ssl_context)
            mailbox.login(EMAIL_USER, EMAIL_PASS, initial_folder='INBOX')
            
            since_date = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
            criteria = AND(seen=False, date_gte=since_date)
            
            for msg in mailbox.fetch(criteria, mark_seen=True):
                print(f"\nNuevo correo de {msg.from_}: {msg.subject}")
                
        return True
    except Exception as e:
        print(f"Error verificando correos: {e}")
        return False

def main():
    """Función principal"""
    print(f"""
    Bot Integrado Nauta.cu + DeltaChat
    ---------------------------------
    Configuración:
    - Nauta: {EMAIL_USER}
    - DeltaChat: {DELTA_CHAT_EMAIL or 'No configurado'}
    - Servidor web: http://0.0.0.0:{os.getenv('PORT', 10000)}
    """)

    # Inicializar bot
    bot = NautaDeltaBot()

    # Hilo para Flask (Render)
    web_thread = threading.Thread(target=run_flask_server, daemon=True)
    web_thread.start()

    # Hilo para DeltaChat (si está configurado)
    if bot.delta_account:
        delta_thread = threading.Thread(
            target=run_cmdline,
            kwargs={"account_plugins": [bot]},
            daemon=True
        )
        delta_thread.start()

    # Bucle principal para Nauta
    while True:
        try:
            print(f"\n[{datetime.now()}] Verificando correos...")
            check_emails()
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nDeteniendo bot...")
            break
        except Exception as e:
            print(f"Error en bucle principal: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()