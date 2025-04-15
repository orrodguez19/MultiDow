from flask import Flask, request, Response
import requests
import urllib3

# Desactivar advertencias de SSL (opcional, para reducir mensajes en la consola)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Redirigir tráfico a https://mined.gob.cu
TARGET_URL = 'https://mined.gob.cu'

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    # Construir la URL completa a la que redirigir el tráfico
    url = TARGET_URL + request.full_path.replace('/proxy', '')

    try:
        # Redirigir la solicitud sin verificar el certificado SSL
        resp = requests.request(
            method=request.method,
            url=url,
            headers=request.headers,
            params=request.args,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            verify=False  # Desactivar verificación SSL
        )

        # Retornar la respuesta del servidor de destino
        return Response(
            resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
    except requests.RequestException as e:
        # Manejar errores de conexión u otros problemas
        return Response(
            f"Error al conectar con {url}: {str(e)}",
            status=502
        )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)