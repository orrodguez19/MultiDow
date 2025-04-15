from flask import Flask, request, Response
import requests

app = Flask(__name__)

# Redirigir tráfico a https://mined.gob.cu
TARGET_URL = 'https://mined.gob.cu'

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    # Construir la URL completa a la que redirigir el tráfico
    url = TARGET_URL + request.full_path.replace('/proxy', '')

    # Redirigir la solicitud
    resp = requests.request(
        method=request.method,
        url=url,
        headers=request.headers,
        params=request.args,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False
    )

    # Retornar la respuesta del servidor de destino
    return Response(
        resp.content,
        status=resp.status_code,
        headers=dict(resp.headers)
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)