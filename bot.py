import os
import re
import smtplib
import email
import time
import subprocess
import socket
from imapclient import IMAPClient
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pyzmail import PyzMessage
import glob
import ssl

# Configuración específica para Nauta.cu
EMAIL_USER = 'miguelorlandos@nauta.cu'
EMAIL_PASS = 'tu_contraseña'  # Considera usar variables de entorno para mayor seguridad
IMAP_SERVER = 'imap.nauta.cu'
IMAP_PORT = 143  # Puerto no cifrado (requiere STARTTLS)
SMTP_SERVER = 'smtp.nauta.cu'
SMTP_PORT = 25  # Puerto no cifrado (requiere STARTTLS)

# Ajustes especiales para Nauta
SSL_VERIFY = False  # Los certificados de Nauta pueden dar problemas
TIMEOUT = 30  # Tiempo de espera mayor para conexiones lentas

def create_imap_connection():
    """Crea una conexión IMAP segura con Nauta.cu"""
    try:
        # Conexión especial para Nauta (puerto 143 con STARTTLS)
        client = IMAPClient(IMAP_SERVER, port=IMAP_PORT, ssl=False, timeout=TIMEOUT)
        client.starttls(ssl_context=ssl.create_default_context())
        client.login(EMAIL_USER, EMAIL_PASS)
        client.select_folder('INBOX')
        return client
    except Exception as e:
        print(f"Error IMAP Nauta: {str(e)}")
        raise

def create_smtp_connection():
    """Crea una conexión SMTP segura con Nauta.cu"""
    try:
        # Conexión especial para Nauta (puerto 25 con STARTTLS)
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=TIMEOUT)
        server.starttls(context=ssl.create_default_context())
        server.login(EMAIL_USER, EMAIL_PASS)
        return server
    except Exception as e:
        print(f"Error SMTP Nauta: {str(e)}")
        raise

def send_email(to_address, subject, body, attachments=None):
    """Versión adaptada para Nauta.cu"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        if attachments:
            for file in attachments:
                if os.path.exists(file):
                    with open(file, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition',
                                  f'attachment; filename="{os.path.basename(file)}"')
                    msg.attach(part)

        with create_smtp_connection() as server:
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")
        return False

def idle_loop():
    """Bucle principal adaptado para Nauta"""
    print(f"Conectando a {IMAP_SERVER}:{IMAP_PORT}...")
    
    try:
        while True:
            try:
                with create_imap_connection() as client:
                    print("Conexión IMAP establecida. Esperando correos...")
                    
                    while True:
                        client.idle()
                        print("Modo IDLE activado...")
                        time.sleep(60)  # Verificar cada minuto
                        client.idle_done()
                        
                        messages = client.search(['UNSEEN'])
                        for msg_id in messages:
                            process_email(client, msg_id)
                            
            except (TimeoutError, ConnectionError) as e:
                print(f"Error de conexión: {str(e)}. Reconectando en 60 segundos...")
                time.sleep(60)
                
    except KeyboardInterrupt:
        print("\nServidor detenido manualmente")
    except Exception as e:
        print(f"Error crítico: {str(e)}")

if __name__ == '__main__':
    # Verificar dependencias primero
    try:
        subprocess.run(['yt-dlp', '--version'], check=True, 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(['ffmpeg', '-version'], check=True,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("""
        Servidor de Descarga de Videos para Nauta.cu
        -------------------------------------------
        Configuración:
        - IMAP: imap.nauta.cu:143 (STARTTLS)
        - SMTP: smtp.nauta.cu:25 (STARTTLS)
        - Cuenta: miguelorlandos@nauta.cu
        """)
        
        idle_loop()
        
    except subprocess.CalledProcessError:
        print("Error: yt-dlp o ffmpeg no están instalados correctamente")