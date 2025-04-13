import os
import logging
import tempfile
import requests
import asyncio
from threading import Thread
from flask import Flask
from deltachat_rpc_client import Rpc, Bot
from deltachat_rpc_client.event import EventType
from waitress import serve
import humanize

app = Flask(__name__)

# ================= CONFIGURACIÓN =================
class BotConfig:
    # Credenciales ArcaneChat
    EMAIL = "multidown@arcanechat.me"
    PASSWORD = "mO*061119"
    
    # Configuración del servicio
    DISPLAY_NAME = "Uguu Uploader Pro"
    PORT = 10000
    UGUU_URL = "https://uguu.se/api.php?d=upload-tool"
    
    # Límites de archivos
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'pdf', 
        'txt', 'zip', 'mp3', 'ogg', 'doc', 'docx', 'xls', 'xlsx'
    }
# ================================================

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def upload_to_uguu(filepath, filename):
    """Sube archivo a Uguu.se"""
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                BotConfig.UGUU_URL,
                files={'file': (filename, f)},
                timeout=30
            )
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error subiendo archivo: {str(e)}")
        raise RuntimeError("Error al subir el archivo")

async def delta_bot():
    """Bot principal con la nueva API"""
    rpc = Rpc()
    bot = Bot(rpc)
    
    @bot.on(EventType.INCOMING_MESSAGE)
    async def handle_message(event):
        try:
            message = await bot.get_message_by_id(event.message_id)
            chat = await message.chat.create()
            
            if await message.chat.is_group():
                return

            # Comandos de texto
            if message.text:
                cmd = message.text.lower().strip()
                
                if cmd == "/start":
                    await chat.send_text("🤖 Bot activo. Envía un archivo para subirlo a Uguu.se")
                elif cmd == "/help":
                    await chat.send_text("ℹ️ Adjunta un archivo (max 100MB) para obtener un enlace de descarga")
                elif cmd == "/formats":
                    formats = "📁 Formatos soportados:\n" + \
                             "\n".join(f"- {ext.upper()}" for ext in sorted(BotConfig.ALLOWED_EXTENSIONS))
                    await chat.send_text(formats)

            # Manejo de archivos
            elif message.file:
                await process_attachment(message, chat)
                
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            await chat.send_text("⚠️ Error procesando tu mensaje")

    # Configurar cuenta
    account = await rpc.get_account()
    if not await account.is_configured():
        await account.configure(BotConfig.EMAIL, BotConfig.PASSWORD)
        await account.set_config("displayname", BotConfig.DISPLAY_NAME)
        logger.info("Cuenta configurada correctamente")

    logger.info("Bot iniciado")
    await bot.run_forever()

async def process_attachment(message, chat):
    """Procesa archivos adjuntos"""
    tmp_path = None
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(message.file.read())
            tmp_path = tmp_file.name
        
        # Validar archivo
        filename = message.filename
        filesize = os.path.getsize(tmp_path)
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        if filesize > BotConfig.MAX_FILE_SIZE:
            raise ValueError(f"Archivo demasiado grande ({humanize.naturalsize(filesize)} > {humanize.naturalsize(BotConfig.MAX_FILE_SIZE)})")
            
        if ext not in BotConfig.ALLOWED_EXTENSIONS:
            raise ValueError(f"Formato .{ext} no soportado")

        # Subir archivo
        await chat.send_text("⏳ Subiendo archivo...")
        download_url = await upload_to_uguu(tmp_path, filename)
        
        # Respuesta
        await chat.send_text(
            f"✅ Subida exitosa!\n\n"
            f"📄 {filename}\n"
            f"🔗 {download_url}\n\n"
            f"⚠️ Enlace temporal"
        )
        logger.info(f"Archivo subido: {filename}")

    except Exception as e:
        await chat.send_text(f"❌ Error: {str(e)}")
        logger.error(f"Error en subida: {str(e)}")
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.route('/')
def status():
    return {
        "status": "running",
        "service": "Uguu Uploader Bot",
        "version": "2.0",
        "port": BotConfig.PORT
    }

def run_server():
    """Inicia el servidor web"""
    logger.info(f"Servidor iniciado en puerto {BotConfig.PORT}")
    serve(
        app,
        host="0.0.0.0",
        port=BotConfig.PORT,
        threads=4
    )

if __name__ == '__main__':
    try:
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