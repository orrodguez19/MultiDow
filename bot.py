import os
import re
import requests
from flask import Flask, render_template, request, jsonify
from yt_dlp import YoutubeDL
from urllib.parse import unquote
import logging
from datetime import datetime

app = Flask(__name__)

# Configuraciones hardcodeadas
app.config['UPLOAD_FOLDER'] = 'temp'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'webm', 'mkv', 'mov'}
app.config['MAX_VIDEO_SIZE'] = 500 * 1024 * 1024  # 500MB
app.config['TRANSFER_SH_URL'] = 'https://transfer.sh'
app.config['TRANSFER_MAX_DAYS'] = '3'
app.config['PORT'] = 10000
app.config['DEBUG'] = True

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Crear directorio temporal
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_url(url):
    """Valida si la URL es válida y de una plataforma soportada."""
    url_pattern = re.compile(r'https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)')
    supported_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
    if not url_pattern.match(url):
        return False
    try:
        parsed_url = requests.utils.urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        return any(domain.endswith(supported) for supported in supported_domains)
    except:
        return False

def upload_to_transfer(file_path):
    """Sube un archivo a transfer.sh."""
    try:
        with open(file_path, 'rb') as f:
            response = requests.put(
                f"{app.config['TRANSFER_SH_URL']}/{os.path.basename(file_path)}",
                data=f,
                headers={'Max-Days': app.config['TRANSFER_MAX_DAYS']}
            )
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        logger.error(f"Error subiendo archivo: {str(e)}")
        raise RuntimeError("No se pudo subir el archivo. Intenta de nuevo más tarde.")

def cleanup_temp_folder():
    """Limpia archivos temporales antiguos."""
    temp_folder = app.config['UPLOAD_FOLDER']
    now = datetime.now().timestamp()
    max_age = 3600  # 1 hora
    for filename in os.listdir(temp_folder):
        file_path = os.path.join(temp_folder, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age:
                try:
                    os.remove(file_path)
                    logger.info(f"Archivo temporal eliminado: {file_path}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar {file_path}: {str(e)}")

@app.route('/')
def index():
    """Sirve la página principal."""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    """Procesa la URL del video y genera un enlace de descarga."""
    url = unquote(request.form.get('url', '')).strip()
    if not url:
        return jsonify({'error': 'URL no proporcionada'}), 400

    if not validate_url(url):
        return jsonify({'error': 'Plataforma no soportada'}), 400

    file_path = None
    try:
        # Configuración yt-dlp
        ydl_opts = {
            'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: None],
        }

        # Descargar video
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)

        # Validar archivo
        if not allowed_file(file_path):
            return jsonify({'error': 'Formato de archivo no permitido'}), 400

        # Verificar tamaño
        file_size = os.path.getsize(file_path)
        if file_size > app.config['MAX_VIDEO_SIZE']:
            return jsonify({'error': 'Video demasiado grande'}), 400

        # Subir archivo
        download_link = upload_to_transfer(file_path)

        return jsonify({
            'download_link': download_link,
            'video_title': info_dict.get('title', 'video'),
            'thumbnail': info_dict.get('thumbnail', '')
        })

    except Exception as e:
        logger.error(f"Error procesando video: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Archivo temporal eliminado: {file_path}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar {file_path}: {str(e)}")
        cleanup_temp_folder()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=app.config['PORT'], debug=app.config['DEBUG'])