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
import glob
import ssl
from imap_tools import MailBox, AND, MailMessageFlags
from datetime import datetime, timedelta

# Configuración Nauta.cu
EMAIL_USER = 'miguelorlandos@nauta.cu'
EMAIL_PASS = 'tu_contraseña'  # Usar variables de entorno en producción
IMAP_SERVER = 'imap.nauta.cu'
IMAP_PORT = 143  # Puerto con STARTTLS
SMTP_SERVER = 'smtp.nauta.cu'
SMTP_PORT = 25   # Puerto con STARTTLS

# Ajustes optimizados
SSL_VERIFY = False
TIMEOUT = 45  # Mayor tiempo para conexiones lentas
CHECK_INTERVAL = 300  # 5 minutos entre verificaciones

def create_imap_connection():
    """Crea conexión IMAP segura con Nauta usando imap-tools"""
    try:
        ssl_context = ssl.create_default_context()
        if not SSL_VERIFY:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        mailbox = MailBox(IMAP_SERVER, port=IMAP_PORT)
        mailbox.starttls(ssl_context)
        mailbox.login(EMAIL_USER, EMAIL_PASS, initial_folder='INBOX')
        return mailbox
    except Exception as e:
        print(f"[IMAP] Error de conexión: {str(e)}")
        raise

def create_smtp_connection():
    """Crea conexión SMTP segura con Nauta"""
    try:
        ssl_context = ssl.create_default_context()
        if not SSL_VERIFY:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=TIMEOUT)
        server.starttls(context=ssl_context)
        server.login(EMAIL_USER, EMAIL_PASS)
        return server
    except Exception as e:
        print(f"[SMTP] Error de conexión: {str(e)}")
        raise

def send_email(to_address, subject, body, attachments=None):
    """Envía email con adjuntos optimizado para Nauta"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(file_path)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)

        with create_smtp_connection() as server:
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL] Error enviando correo: {str(e)}")
        return False

def process_email(msg):
    """Procesa un correo entrante"""
    try:
        print(f"\nNuevo correo recibido:")
        print(f"De: {msg.from_}")
        print(f"Asunto: {msg.subject}")
        print(f"Fecha: {msg.date}")
        
        # Procesar texto del correo
        if msg.text:
            print("\nContenido:")
            print(msg.text[:500] + "..." if len(msg.text) > 500 else msg.text)
        
        # Procesar adjuntos
        if msg.attachments:
            print(f"\nAdjuntos ({len(msg.attachments)}):")
            for adj in msg.attachments:
                print(f"- {adj.filename} ({len(adj.payload)} bytes)")
                
                # Guardar adjuntos en una carpeta
                download_dir = "email_attachments"
                os.makedirs(download_dir, exist_ok=True)
                filepath = os.path.join(download_dir, adj.filename)
                
                with open(filepath, 'wb') as f:
                    f.write(adj.payload)
                print(f"Guardado en: {filepath}")
        
        # Aquí puedes añadir tu lógica de procesamiento de videos
        # Ejemplo: buscar enlaces de YouTube en el texto
        youtube_links = re.findall(r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)', msg.text or "")
        if youtube_links:
            print("\nEnlaces de YouTube detectados:")
            for link in youtube_links:
                print(f"- {link}")
                # Aquí podrías llamar a yt-dlp para descargar
                # download_video(link)
        
        return True
    except Exception as e:
        print(f"[PROCESO] Error procesando correo: {str(e)}")
        return False

def check_emails():
    """Verifica correos nuevos de forma activa (polling)"""
    try:
        with create_imap_connection() as mailbox:
            # Buscar correos no leídos de los últimos 7 días
            since_date = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
            criteria = AND(seen=False, date_gte=since_date)
            
            for msg in mailbox.fetch(criteria, mark_seen=True):
                if process_email(msg):
                    # Opcional: Marcar como leído después de procesar
                    mailbox.seen(msg.uid, True)
                    
            return True
    except Exception as e:
        print(f"[CHECK] Error verificando correos: {str(e)}")
        return False

def main_loop():
    """Bucle principal mejorado"""
    print(f"""
    Servidor de Descarga para Nauta.cu
    ----------------------------------
    Configuración:
    - IMAP: {IMAP_SERVER}:{IMAP_PORT} (STARTTLS)
    - SMTP: {SMTP_SERVER}:{SMTP_PORT} (STARTTLS)
    - Cuenta: {EMAIL_USER}
    - Intervalo de verificación: {CHECK_INTERVAL} segundos
    """)
    
    # Verificar dependencias
    try:
        subprocess.run(['yt-dlp', '--version'], check=True, 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(['ffmpeg', '-version'], check=True,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: yt-dlp o ffmpeg no están instalados correctamente")
        return
    
    # Bucle principal
    while True:
        try:
            print(f"\n[{datetime.now()}] Verificando correos...")
            check_emails()
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nServidor detenido manualmente")
            break
        except Exception as e:
            print(f"[LOOP] Error crítico: {str(e)}")
            print("Reintentando en 60 segundos...")
            time.sleep(60)

if __name__ == '__main__':
    main_loop()