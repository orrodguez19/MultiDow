from flask import Flask, request, Response, send_from_directory, jsonify
import requests
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
TARGET_URL = 'https://mined.gob.cu'
UPLOAD_FOLDER = 'uploaded_files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/proxy', defaults={'path': ''}, methods=['GET', 'POST', 'DELETE'])
@app.route('/proxy/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy(path):
    internal_paths = ['upload', 'download', 'files', 'delete']

    if path.startswith('upload') and request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó ningún archivo'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        return jsonify({'message': 'Archivo subido exitosamente', 'filename': file.filename})

    elif path.startswith('download/') and request.method == 'GET':
        filename = path.replace('download/', '', 1)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.isfile(filepath):
            return jsonify({'error': 'Archivo no encontrado'}), 404
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

    elif path == 'files' and request.method == 'GET':
        files = os.listdir(UPLOAD_FOLDER)
        return jsonify({'files': files})

    elif path.startswith('delete/') and request.method == 'DELETE':
        filename = path.replace('delete/', '', 1)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
            return jsonify({'message': 'Archivo eliminado correctamente'})
        else:
            return jsonify({'error': 'Archivo no encontrado'}), 404

    # Ruta externa
    url = f"{TARGET_URL}/{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=request.headers,
            params=request.args,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            verify=False
        )
        return Response(resp.content, status=resp.status_code, headers=dict(resp.headers))
    except requests.RequestException as e:
        return Response(f"Error al conectar con {url}: {str(e)}", status=502)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)