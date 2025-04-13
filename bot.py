from flask import Flask, request, jsonify
import imaplib
import smtplib
import email
from email.header import decode_header
import yt_dlp as yt_dl
import os
import subprocess

app = Flask(__name__)

# Configuración de la cuenta de correo (las credenciales directamente en el código)
EMAIL = "orrodriguez588@gmail.com"  # Tu correo electrónico
PASSWORD = "cnkpjyridpqcbclu"  # Tu contraseña de correo
SMTP_SERVER = "smtp.gmail.com"  # Servidor SMTP para Gmail (o el que uses)
IMAP_SERVER = "imap.gmail.com"  # Servidor IMAP para Gmail (o el que uses)

# Conectar al servidor de correo (IMAP)
def connect_to_mail():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    return mail

# Buscar correos no leídos
def check_new_emails(mail):
    mail.select("inbox")
    status, messages = mail.search(None, 'UNSEEN')  # Obtener mensajes no leídos
    if status != "OK":
        print("Error al obtener mensajes")
        return []
    email_ids = messages[0].split()
    return email_ids

# Descargar vídeo de YouTube con calidad media (720p o similar)
def download_video(url, quality="bestvideo[height<=720]+bestaudio"):
    options = {
        'format': quality,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True  # Para no descargar listas de reproducción
    }
    with yt_dl.YoutubeDL(options) as ydl:
        ydl.download([url])

# Comprimir vídeo sin perder calidad con calidad media
def compress_video(input_video, output_video):
    # Usamos ffmpeg para comprimir el vídeo sin perder mucha calidad
    command = [
        'ffmpeg', 
        '-i', input_video, 
        '-c:v', 'libx264',  # Usar el codec de vídeo H.264
        '-crf', '23',  # Calidad media (puedes ajustar si deseas más calidad o menos)
        '-preset', 'medium',  # Control de la velocidad de compresión (medium es un buen equilibrio)
        '-c:a', 'aac',  # Usar el codec de audio AAC
        output_video
    ]
    subprocess.run(command, check=True)

# Enviar el vídeo al remitente
def send_email_with_attachment(to_email, subject, body, attachment_path):
    msg = email.mime.multipart.MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(email.mime.text.MIMEText(body, 'plain'))
    
    with open(attachment_path, "rb") as f:
        attach = email.mime.base.MIMEBase('application', 'octet-stream')
        attach.set_payload(f.read())
        email.encoders.encode_base64(attach)
        attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
        msg.attach(attach)
    
    with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, to_email, msg.as_string())

# Ruta para recibir correos nuevos
@app.route('/check_emails', methods=['GET'])
def check_emails():
    mail = connect_to_mail()
    email_ids = check_new_emails(mail)
    if not email_ids:
        return jsonify({"message": "No new emails."}), 200
    
    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            continue
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8')
                
                # Buscar enlaces en el cuerpo del mensaje
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        urls = [word for word in body.split() if "youtube.com" in word]
                        
                        for url in urls:
                            print(f"Enlace encontrado: {url}")
                            
                            # Descargar el vídeo con calidad media (720p)
                            download_video(url, quality="bestvideo[height<=720]+bestaudio")
                            
                            # Comprimir el vídeo después de la descarga
                            downloaded_video = "downloads/ejemplo_video.mp4"
                            compressed_video = "downloads/compressed_video.mp4"
                            compress_video(downloaded_video, compressed_video)
                            
                            # Enviar el vídeo comprimido al remitente
                            send_email_with_attachment(msg["From"], "Aquí está tu vídeo comprimido", 
                                                       "Te envío el vídeo solicitado.", compressed_video)

    mail.store(email_id, '+FLAGS', '\\Seen')  # Marcar el mensaje como leído
    return jsonify({"message": "Emails processed."}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)  # El puerto 5000 es común en entornos de desarrollo