import os
import time
import threading
import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from flask import Flask
from yt_dlp import YoutubeDL
from hurry.filesize import size

EMAIL = "orrodriguez588@gmail.com"
PASSWORD = "cnkpjyridpqcbclu"
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
IMAP_PORT = 993
SMTP_PORT = 587

DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB para DeltaChat
CHECK_INTERVAL = 20  # segundos

app = Flask(__name__)

@app.route("/")
def home():
    return "DeltaChat bot is running!"

def download_video(url, audio_only=False):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    filename = None
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }

    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        })

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if audio_only:
            filename = filename.rsplit('.', 1)[0] + '.mp3'
        return filename, info.get("title")

def send_email(to_address, subject, body, attachment_path=None):
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = to_address
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)

def process_email(msg):
    from_address = email.utils.parseaddr(msg["From"])[1]
    subject = msg["Subject"]
    payload = msg.get_payload(decode=True).decode(errors="ignore")

    if "/download" in payload or "/audio" in payload:
        try:
            is_audio = "/audio" in payload
            url = payload.split()[-1]
            filepath, title = download_video(url, audio_only=is_audio)

            file_size = os.path.getsize(filepath)
            if file_size > MAX_FILE_SIZE:
                send_email(from_address, "Archivo demasiado grande",
                           f"{title} excede el límite de {size(MAX_FILE_SIZE)}.")
            else:
                send_email(from_address, f"{title}", "Aquí tienes tu archivo", filepath)
        except Exception as e:
            send_email(from_address, "Error de descarga", str(e))

def check_emails():
    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(EMAIL, PASSWORD)
            mail.select("inbox")

            result, data = mail.search(None, '(UNSEEN)')
            ids = data[0].split()

            for num in ids:
                result, data = mail.fetch(num, "(RFC822)")
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                process_email(msg)

            mail.logout()
        except Exception as e:
            print(f"[ERROR IMAP]: {e}")

        time.sleep(CHECK_INTERVAL)

def start_email_thread():
    thread = threading.Thread(target=check_emails)
    thread.daemon = True
    thread.start()

if __name__ == "__main__":
    start_email_thread()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))