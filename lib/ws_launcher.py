import logging
import threading
from config import XnoppoConfig

logger = logging.getLogger(__name__)

def start_ws_thread(config: XnoppoConfig):
    """Start the Emby WebSocket listener in a background thread."""
    logger.info("Checking if WebSocket thread should start...")
    srv = config.get("emby_server")
    usr = config.get("user_name")
    
    if not srv or not usr:
        logger.warning("WebSocket thread NOT started: emby_server='%s', user_name='%s'", srv, usr)
        return

    try:
        from lib.emby_ws import EmbyWebSocketClient
        ws_client = EmbyWebSocketClient(config)
        config.set_ws_client(ws_client)
        
        thread = threading.Thread(target=ws_client.start, daemon=True)
        thread.start()
        logger.info("Emby WebSocket thread STARTED successfully")
    except Exception as e:
        logger.error("CRITICAL: Could not start WebSocket thread: %s", e, exc_info=True)
