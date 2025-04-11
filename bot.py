import os
import requests
from flask import Flask, render_template, request, jsonify
from yt_dlp import YoutubeDL
from urllib.parse import unquote

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'webm', 'mkv', 'mov'}

# Crear directorio temporal si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def upload_to_transfer(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.put(
                f'https://transfer.sh/{os.path.basename(file_path)}',
                data=f,
                headers={'Max-Days': '3'}  # Archivo disponible por 3 días
            )
        return response.text.strip()
    except Exception as e:
        raise RuntimeError(f'Error subiendo archivo: {str(e)}')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = unquote(request.form.get('url', '')).strip()
    if not url:
        return jsonify({'error': 'URL no proporcionada'}), 400
    
    try:
        # Configuración yt-dlp
        ydl_opts = {
            'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], '%(title)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: None]  # Necesario para evitar errores
        }

        # Descargar video
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)

        # Validar y subir archivo
        if not allowed_file(file_path):
            raise ValueError('Formato de archivo no permitido')
        
        download_link = upload_to_transfer(file_path)
        os.remove(file_path)  # Limpiar archivo temporal

        return jsonify({
            'download_link': download_link,
            'video_title': info_dict.get('title', 'video'),
            'thumbnail': info_dict.get('thumbnail', '')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)