import os
import re
import requests
import smtplib
import email
import time
from imapclient import IMAPClient
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from pyzmail import PyzMessage

# Cargar variables de entorno
load_dotenv()

EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
IMAP_SERVER = os.getenv('IMAP_SERVER')
IMAP_PORT = int(os.getenv('IMAP_PORT'))
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT'))

# Patrón regex para encontrar URLs en el texto
URL_REGEX = r'https?://\S+'

def download_file(url):
    """Descarga un archivo desde una URL y lo guarda en el directorio actual."""
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def send_email(to_address, subject, body, attachments):
    """Envía un correo electrónico con los archivos adjuntos especificados."""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = to_address
    msg['Subject'] = subject

    # Adjuntar cuerpo del mensaje
    msg.attach(email.mime.text.MIMEText(body, 'plain'))

    # Adjuntar archivos
    for file in attachments:
        attachment = MIMEBase('application', 'octet-stream')
        with open(file, 'rb') as f:
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename={file}')
        msg.attach(attachment)

    # Enviar el correo
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def process_email(mailbox, msg_id):
    """Procesa un correo electrónico: descarga archivos de enlaces y responde con los archivos adjuntos."""
    response = mailbox.fetch([msg_id], ['RFC822'])
    raw_email = response[msg_id][b'RFC822']
    msg = PyzMessage.factory(raw_email)

    # Obtener el remitente
    from_address = msg.get_address('from')[1]

    # Extraer enlaces del cuerpo del mensaje
    urls = re.findall(URL_REGEX, msg.text_part.get_payload().decode(msg.text_part.charset) if msg.text_part else '')

    # Descargar archivos desde los enlaces
    downloaded_files = []
    for url in urls:
        try:
            downloaded_file = download_file(url)
            downloaded_files.append(downloaded_file)
        except Exception as e:
            print(f"Error al descargar {url}: {e}")

    # Responder al remitente con los archivos adjuntos
    if downloaded_files:
        send_email(from_address, 'Archivos descargados', 'Adjunto encontrarás los archivos solicitados.', downloaded_files)

        # Eliminar archivos descargados
        for file in downloaded_files:
            os.remove(file)

def idle_loop():
    """Bucle principal que escucha nuevos correos y los procesa."""
    with IMAPClient(IMAP_SERVER, port=IMAP_PORT) as client:
        client.login(EMAIL_USER, EMAIL_PASS)
        client.select_folder('INBOX')

        while True:
            # Escuchar nuevos correos
            client.idle()
            print("Esperando nuevos correos...")
            time.sleep(60)  # Verificar cada 60 segundos
            client.idle_done()

            # Buscar correos no leídos
            messages = client.search(['UNSEEN'])
            for msg_id in messages:
                process_email(client, msg_id)

if __name__ == '__main__':
    idle_loop()