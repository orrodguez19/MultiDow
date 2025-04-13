import os
import logging
import tempfile
import requests
import re
import asyncio
from threading import Thread
from flask import Flask
from deltachat_rpc_client import Rpc, Bot, Events
from waitress import serve
import humanize
from datetime import datetime

app = Flask(__name__)

# ================= CONFIGURACIÓN =================
class BotConfig:
    # Credenciales ArcaneChat
    EMAIL = "miguelorlandos@nauta.cu"
    PASSWORD = "TdrPQQxq"
    
    # Configuración del servicio
    DISPLAY_NAME = "Uguu Uploader Pro"
    PORT = 10000
    UGUU_URL = "https://uguu.se/api.php?d=upload-tool"
    
    # Configuración del servidor
    SERVER_CONFIG = {
        "mail_server": "imap.nauta.cu",
        "mail_port": "143",
        "send_server": "smtp.nauta.cu",
        "send_port": "25",
    }
    
    # Límites y optimización
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'pdf', 
        'txt', 'zip', 'mp3', 'ogg', 'doc', 'docx', 'xls', 'xlsx'
    }
    MESSAGE_QUEUE_SIZE = 50
    PROCESSING_TIMEOUT = 15  # segundos
# ================================================

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('uguu_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_config():
    """Valida la configuración crítica"""
    assert re.match(r"^[^@]+@arcanechat\.me$", BotConfig.EMAIL), "Email inválido"
    assert len(BotConfig.PASSWORD) >= 8, "Contraseña muy corta"
    assert 1024 <= BotConfig.PORT <= 65535, "Puerto inválido"

async def upload_to_uguu(filepath, filename):
    """Sube archivo a Uguu.se con timeout"""
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                BotConfig.UGUU_URL,
                files={'file': (filename, f)},
                timeout=BotConfig.PROCESSING_TIMEOUT
            )
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        logger.error(f"Subida fallida: {str(e)}")
        raise RuntimeError("Error temporal en el servicio")

async def delta_bot():
    """Bot principal con gestión de colas"""
    rpc = Rpc()
    bot = Bot(rpc)
    
    @bot.on(Events.INCOMING_MSG)
    async def handle_message(event):
        try:
            start_time = datetime.now()
            message = await bot.get_message_by_id(event.msg_id)
            chat = await message.chat.create()
            
            # Ignorar grupos
            if await message.chat.is_group():
                return

            # Respuesta INSTANTÁNEA para comandos
            if message.text:
                cmd = message.text.lower().strip()
                
                if cmd == "/start":
                    await chat.send_text("🔄 Procesando tu solicitud...")
                    asyncio.create_task(send_full_response(chat, "menu"))
                    return
                    
                elif cmd in ("/help", "/ayuda"):
                    await chat.send_text("📚 Preparando ayuda...")
                    asyncio.create_task(send_full_response(chat, "help"))
                    return
                    
                elif cmd == "/formats":
                    await chat.send_text("📂 Buscando formatos...")
                    asyncio.create_task(send_full_response(chat, "formats"))
                    return
            
            # Manejo de archivos en segundo plano
            if message.file and message.filename:
                await chat.send_text("⏳ Recibí tu archivo, iniciando proceso...")
                asyncio.create_task(process_attachment(message, chat))
                
            logger.info(f"Mensaje procesado en {(datetime.now() - start_time).total_seconds():.2f}s")
                
        except Exception as e:
            logger.error(f"Error en mensaje: {str(e)}")
            await chat.send_text("⚠️ Error temporal, intenta nuevamente")

    # Configuración de cuenta
    account = await rpc.get_account()
    if not await account.is_configured():
        await account.configure(BotConfig.EMAIL, BotConfig.PASSWORD)
        await account.set_config("displayname", BotConfig.DISPLAY_NAME)
        for key, value in BotConfig.SERVER_CONFIG.items():
            await account.set_config(key, value)
        logger.info("Cuenta configurada")

    logger.info("Bot iniciado (Respuestas instantáneas activas)")
    await bot.run_forever()

# ================= RESPUESTAS RÁPIDAS =================
async def send_full_response(chat, response_type):
    """Envía respuestas completas en segundo plano"""
    try:
        if response_type == "menu":
            text = """
🛠️ *Uguu Uploader Bot* 🛠️

Envía archivos (hasta 100MB) y recibe enlaces directos.

📋 *Comandos:*
/help - Muestra ayuda
/formats - Formatos soportados
"""
        elif response_type == "help":
            text = """
📌 *Ayuda Rápida*

1. Adjunta archivos (fotos, videos, docs)
2. Espera el enlace de descarga
3. Comparte el enlace

🛑 *Límites:*
- Máximo 100MB por archivo
- Usa /formats para ver extensiones
"""
        else:  # formats
            text = "📁 *Formatos soportados:*\n" + \
                  "\n".join(f"- {ext.upper()}" for ext in sorted(BotConfig.ALLOWED_EXTENSIONS))
        
        await chat.send_text(text.strip())
        
    except Exception as e:
        logger.error(f"Error enviando {response_type}: {str(e)}")

async def process_attachment(message, chat):
    """Procesamiento completo de archivos en segundo plano"""
    tmp_path = None
    try:
        # Descargar adjunto
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(message.file.read())
            tmp_path = tmp_file.name
        
        file_info = {
            'name': message.filename,
            'size': os.path.getsize(tmp_path),
            'path': tmp_path
        }

        # Validaciones rápidas
        if file_info['size'] > BotConfig.MAX_FILE_SIZE:
            raise ValueError(
                f"Archivo demasiado grande ({humanize.naturalsize(file_info['size'])})"
            )
            
        ext = file_info['name'].split('.')[-1].lower() if '.' in file_info['name'] else ''
        if ext not in BotConfig.ALLOWED_EXTENSIONS:
            raise ValueError(f"Formato .{ext} no soportado")

        # Subir a Uguu
        await chat.send_text("⬆️ Subiendo a Uguu.se...")
        download_url = await upload_to_uguu(tmp_path, file_info['name'])
        
        # Respuesta final
        await chat.send_text(
            f"✅ *Subida exitosa!*\n\n"
            f"📄: {file_info['name']}\n"
            f"🔗: {download_url}\n\n"
            f"⚠️ Enlace temporal"
        )
        logger.info(f"Archivo subido: {file_info['name']}")

    except Exception as e:
        await chat.send_text(f"❌ Error: {str(e)}")
        logger.error(f"Error en subida: {str(e)}")
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

# ================= SERVIDOR WEB =================
@app.route('/')
def status():
    return {
        "status": "running",
        "service": "Uguu-Uploader-Bot",
        "response_time": "instant",
        "port": BotConfig.PORT
    }, 200

def run_server():
    """Inicia servidor de producción con Waitress"""
    logger.info(f"🚀 Servidor iniciado en puerto {BotConfig.PORT}")
    serve(
        app,
        host="0.0.0.0",
        port=BotConfig.PORT,
        threads=4,
        channel_timeout=60
    )

if __name__ == '__main__':
    try:
        validate_config()
        logger.info("Iniciando servicios...")
        
        # Iniciar bot en segundo plano
        Thread(
            target=asyncio.run,
            args=(delta_bot(),),
            daemon=True
        ).start()
        
        # Iniciar servidor web
        run_server()
        
    except Exception as e:
        logger.critical(f"Error de inicio: {str(e)}")
        exit(1)