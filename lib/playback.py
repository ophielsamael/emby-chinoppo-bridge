"""
Playback Orchestrator — Xnoppo
Extracted and refactored from the original monolithic playto_file() / playother() functions.
"""

import logging
import os
import threading
import time as _time

from .oppo import OppoClient
from .emby_http import EmbyHttpClient, EmbyConnectionError

logger = logging.getLogger(__name__)

# Global tracker to handle race conditions between threads
_active_session_id = 0
_session_lock = threading.Lock()

def get_next_id():
    global _active_session_id
    with _session_lock:
        _active_session_id += 1
        return _active_session_id

def _is_session_active(session_id):
    global _active_session_id
    return _active_session_id == session_id


def _translate_path(movie: str, server_list: list) -> str:
    """Replace Emby paths with Oppo-accessible paths."""
    for server in server_list:
        movie = movie.replace(server.get("Emby_Path", ""), server.get("Oppo_Path", ""))
    movie = movie.replace("\\\\", "\\").replace("\\", "/")
    return movie


def play_to_file(session: EmbyHttpClient, data: dict, config: dict):
    """Orchestrate full playback: connect → mount → play → monitor → cleanup."""
    try:
        _orchestrate_playback(session, data, config)
    except Exception as e:
        logger.exception("Critical error in playback orchestrator: %s", e)
        session.playstate = "Free"
        _notify_user(session, session.process_data(data), f"Xnoppo Error: {str(e)}", config, timeout_ms=8000)


def _orchestrate_playback(session: EmbyHttpClient, data: dict, config: dict):
    # Use the ID assigned by the WS trigger, or get a new one if manual
    my_id = data.get("Session_Internal_Id") or get_next_id()
    logger.info("Iniciando sesión de orquestación #%d", my_id)

    session.playstate = "Loading"
    session.currentdata = data
    params = session.process_data(data)
    client = OppoClient(
        config["Oppo_IP"],
        connection_timeout=config.get("timeout_oppo_conection", 10),
        mount_timeout=config.get("timeout_oppo_mount", 60),
        play_timeout=config.get("timeout_oppo_playitem", 60),
    )

    # 1. Wake up / Check connection
    try:
        if client.check_connection() != 0:
            logger.info("Oppo en Standby o durmiendo. Enviando orden de encendido...")
            client.send_notify_remote()
            client.send_remote_key("PON")
            for i in range(10):
                _time.sleep(2)
                if client.check_connection() == 0:
                    logger.info("Oppo listo después de %ds", (i+1)*2)
                    break
            else:
                logger.error("El Oppo no ha despertado a tiempo.")
                session.playstate = "Free"
                return
    except Exception as e:
        logger.error("Error crítico al despertar Oppo: %s", e)
        session.playstate = "Free"
        return

    # Get item info from Emby
    item_info = session.get_item_info2(
        session.user_info["User"]["Id"], params["item_id"], params["media_source_id"]
    )

    file_path = item_info.get("Path", "")
    container = item_info.get("Container", "")
    
    # ISO fix: Sometimes Path is empty at top level, but present in MediaSources
    if not file_path:
        for source in item_info.get("MediaSources", []):
            if source.get("Path"):
                file_path = source.get("Path")
                container = source.get("Container", container).lower()
                logger.info("Ruta recuperada desde MediaSources: %s (Container: %s)", file_path, container)
                break

    # 1. IMMEDIATE STOP of internal playback (Kill it as fast as possible)
    try:
        if params.get("Session_id"):
            session.playback_stop(params["Session_id"])
            logger.info("Stopped original Emby session: %s", params["Session_id"])
    except Exception as e:
        logger.warning("Could not stop original session: %s", e)

    # 2. Notify user
    _notify_user(session, params, "Xnoppo: Cargando en Oppo...", config)

    # Initialize Oppo
    client.get_firmware_version()
    client.get_device_list()
    client.get_setup_menu()
    client.sign_in()
    client.get_global_info()
    
    # AV Control - Remember current input (but don't switch yet!)
    if config.get("AV"):
        try:
            from .av_control import av_check_power, av_get_current_input
            av_check_power(config)
            
            # Remember current input before switching
            original_input = av_get_current_input(config)
            if original_input:
                logger.info("Guardando entrada AV original para restauración: %s", original_input.strip())
                config["_original_av_input"] = original_input
                
        except Exception as e:
            logger.error("AV control failed during startup: %s", e)
    
    # Oppo Mounting
    _time.sleep(1)
    client.get_setup_menu()

    # Translate path
    movie = _translate_path(file_path, config.get("servers", []))
    parsed = OppoClient.parse_media_path(movie)
    server_name = parsed["server"]
    folder = parsed["folder"]
    filename = parsed["filename"]

    # Synology volume1 detection fix
    if server_name.lower().startswith("volume"):
        logger.info("Detectado error común de Synology: '%s' no es un servidor, es un volumen.", server_name)
        # Restore the full path for later mounting
        folder = server_name + "/" + folder if folder else server_name

    session.server = server_name
    session.folder = folder
    session.filename = filename
    session.playedtitle = item_info.get("Name", "")

    logger.info("Playing: server=%s folder=%s file=%s", server_name, folder, filename)

    # Intelligent Server Name Resolution (Wait for it to appear in network)
    try:
        devices = client.get_device_list()
    except Exception:
        devices = {"devicelist": []}
    
    actual_server = server_name
    dev_list = devices.get("devicelist", [])
    
    # Search for server in list
    found_dev = next((d for d in dev_list if d.get("name", "").upper() == server_name.upper()), None)
    
    # Synology Fix: If server is 'volumeX', pick the first NFS/SMB server available or use Emby IP
    if not found_dev and server_name.lower().startswith("volume"):
        # Try to find any NFS server first (preferred for Synology)
        found_dev = next((d for d in dev_list if d.get("sub_type") == "nfs"), None)
        if not found_dev:
            # Fallback to any server
            found_dev = dev_list[0] if dev_list else None
        
        if found_dev:
            logger.info("Auto-resolviendo volumen '%s' al servidor: '%s'", server_name, found_dev.get("name"))
            actual_server = found_dev.get("name")
        else:
            # Last resort: Extract IP from emby_server URL
            emby_url = config.get("emby_server", "")
            if emby_url:
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(emby_url)
                    extracted_ip = parsed_url.hostname or parsed_url.netloc.split(":")[0]
                    if extracted_ip and extracted_ip not in ["127.0.0.1", "localhost", ""]:
                        logger.info("Usando IP extraída de Emby como servidor de respaldo: %s", extracted_ip)
                        actual_server = extracted_ip
                    else:
                        actual_server = "192.168.1.17" # Hardcoded backup based on user environment
                except Exception:
                    actual_server = "192.168.1.17"
            else:
                logger.warning("No se pudo auto-resolver el servidor. Usando IP por defecto.")
                actual_server = "192.168.1.17"

    nfs = OppoClient.detect_nfs(actual_server, devices, config.get("default_nfs", False))
    server_name = actual_server

    # ── Login to NFS/SMB share ────────────────────────────────────────────────
    # NOTE: Do NOT call unmount() before login — if nothing is mounted, the Oppo
    # blocks for ~20s on the unmount command and corrupts its NFS client state.
    # The simple login→mount sequence worked reliably in earlier versions.
    logger.info("Conectando al servidor: %s (%s)", server_name, "NFS" if nfs else "SMB")
    if nfs:
        client.login_nfs(server_name)
        client.get_nfs_share_list()
    else:
        client.login_smb(server_name)
        client.get_smb_share_list()

    if not config.get("Always_ON"):
        _time.sleep(2)
    client.get_setup_menu()

    # ── Mount (Exact Path) ────────────────────────────────────────────────────
    # WARNING: Do NOT add a leading slash to the folder path!
    # The original Xnoppo code explicitly sent the folder string EXACTLY as parsed 
    # (e.g., "volume1/Plex/Library/ATMOS" without a leading slash). Adding a leading 
    # slash causes the Oppo NFS client to return 'failed'.
    mount_folder = folder.lstrip("/")  # Strip leading slashes to match v2 behavior

    _notify_user(session, params, "Xnoppo: Montando...", config, timeout_ms=1999)

    mount_result = None
    for mount_attempt in range(2):
        logger.info("Intentando montar: server=%s folder='%s'", server_name, mount_folder)
        if nfs:
            mount_result = client.mount_nfs(server_name, mount_folder)
        else:
            mount_result = client.mount_smb(server_name, mount_folder)

        if mount_result.get("success"):
            logger.info("Montaje exitoso en intento %d", mount_attempt + 1)
            break

        if mount_attempt == 0:
            logger.warning("Intento 1/2 fallido (%s). Re-login y reintento...", mount_result.get("retInfo", "?"))
            # Fresh login only — NO unmount (unmount blocks and corrupts state)
            _time.sleep(2)
            if nfs:
                client.login_nfs(server_name)
                client.get_nfs_share_list()
            else:
                client.login_smb(server_name)
                client.get_smb_share_list()
            client.get_setup_menu()

    if not mount_result or not mount_result.get("success"):
        error = mount_result.get("retInfo", "unknown") if mount_result else "sin respuesta"
        logger.error("Error de montaje en %s / %s: %s", server_name, mount_folder, error)
        _notify_user(session, params, f"Xnoppo: Error de montaje: {error}", config, timeout_ms=5000)
        session.playstate = "Free"
        return

    # ── Play ──────────────────────────────────────────────────────────────────
    play_filename = filename
    is_iso = filename.lower().endswith(".iso") or container.lower() == "iso"

    logger.info("Enviando orden de reproducción: server=%s, file=%s (ISO=%s)", server_name, play_filename, is_iso)

    if is_iso:
        logger.info("Modo ISO: enviando STP y esperando 4s antes de reproducir...")
        client.send_remote_key("STP")
        _time.sleep(4)
        play_result = client.play_file(server_name, play_filename, "0", nfs)
    elif container in ("bluray", "bd25", "bd50"):
        play_result = client.check_folder_has_bdmv(play_filename, nfs)
        if not play_result.get("success"):
            play_result = client.play_file(server_name, play_filename, "0", nfs)
    else:
        play_result = client.play_file(server_name, play_filename, "0", nfs)

    if not play_result.get("success"):
        error = play_result.get("retInfo") or play_result.get("msg", "unknown")
        logger.error("Error al reproducir %s: %s", filename, error)
        _notify_user(session, params, f"Xnoppo: Error al reproducir: {error}", config, timeout_ms=5000)
        session.playstate = "Free"  # Reset state WITHOUT powering off Oppo
        return

    # Wait for video to ACTUALLY start playing
    # For ISOs, this can take up to 90 seconds (large file buffering + disc menu loading)
    timeout = config.get("timeout_oppo_playitem", 60)
    if is_iso:
        timeout = max(timeout, 90) # ISOs need more patience
    
    timer = 0
    logger.info("Esperando confirmación de reproducción del Oppo (timeout: %ds)...", timeout)
    while timer < timeout:
        _time.sleep(2)
        timer += 2
        try:
            global_info = client.get_global_info()
        except Exception:
            continue
        
        # Check if we were superseded before waiting finished
        if not _is_session_active(my_id):
            logger.info("Sesión #%d reemplazada durante carga. Salida silenciosa.", my_id)
            return
        
        if '"is_video_playing":true' in global_info:
            logger.info("Oppo confirmó reproducción activa tras %ds.", timer)
            break
            
        # Self-healing: If ISO hasn't started after 20s, re-send play command once
        if is_iso and timer == 20:
            logger.info("ISO no ha arrancado tras 20s. Re-enviando comando de reproducción (Auto-Heal)...")
            client.play_file(server_name, play_filename, "0", nfs)
        
        _notify_user(session, params, f"Xnoppo: Cargando... {timer}s", config, timeout_ms=1999)
    else:
        logger.warning("Timeout esperando reproducción activa en Oppo (%ds). Abortando.", timeout)
        _cleanup(session, client, config)
        return

    # Video started
    session.playstate = "Playing"
    session.playnow(data)

    # Set resume position
    resume = params.get("auto_resume", 0)
    client.set_play_time(resume if resume > 0 else 0)

    # Set audio track
    try:
        audio_idx = session.get_xnoppo_audio_index(
            params["ControllingUserId"], params["item_id"], params["audio_stream_index"]
        )
        client.set_audio_track(audio_idx)
    except Exception:
        pass

    # TV HDMI switch
    if config.get("TV"):
        try:
            from .tv_control import tv_change_hdmi
            tv_change_hdmi(config)
        except Exception as e:
            logger.warning("TV HDMI change failed: %s", e)

    # AV HDMI switch
    if config.get("AV"):
        try:
            _time.sleep(config.get("av_delay_hdmi", 0))
            from .av_control import av_change_hdmi
            av_change_hdmi(config)
        except Exception as e:
            logger.warning("AV HDMI change failed: %s", e)

    # Set subtitles
    try:
        subs_idx = session.get_xnoppo_subs_index(
            params["ControllingUserId"], params["item_id"], params["subtitle_stream_index"]
        )
        client.set_subtitle_track(subs_idx)
    except Exception:
        pass

    # Monitor playback progress
    position_ticks = 0
    total_ticks = 0
    is_paused = False
    is_muted = False
    global_info = client.get_global_info()

    while True:
        _time.sleep(1)
        
        # Check if we were superseded by a newer session
        if not _is_session_active(my_id):
            logger.info("Sesión #%d interrumpida por una más nueva. Salida silenciosa.", my_id)
            return

        if session.playstate == "Replay":
            logger.info("Replay detectado en sesión #%d — cediendo control.", my_id)
            return # EXIT IMMEDIATELY without calling _cleanup
            
        global_info = client.get_global_info()
        
        # If video stops, wait 5s to see if it's just an ISO transition (intro -> movie)
        if '"is_video_playing":true' not in global_info:
            logger.debug("Vídeo detenido en sesión #%d. Esperando 5s por posible transición...", my_id)
            _time.sleep(5)
            global_info = client.get_global_info()
            if '"is_video_playing":true' not in global_info:
                logger.info("Vídeo detenido definitivamente en sesión #%d.", my_id)
                break
            else:
                logger.info("Transición de ISO detectada. Continuando monitorización.")

        if '"is_video_playing":true' in global_info:
            try:
                pt = client.get_playing_time()
                cur = pt.get("cur_time", 0)
                tot = pt.get("total_time", 0)
                if cur > 0 and tot > 0:
                    position_ticks = cur * 10_000_000
                    total_ticks = tot * 10_000_000
            except Exception:
                pass
            try:
                session.playing_progress(data, position_ticks, total_ticks, is_paused, is_muted)
                session.set_playback_position(data, position_ticks, False)
            except Exception:
                pass

    # Playback finished
    try:
        session.playing_stopped(data, position_ticks, is_paused, is_muted)
        total_secs = total_ticks / 10_000_000 if total_ticks > 0 else 1
        played = (position_ticks / total_secs) > 0.95 if total_secs > 0 else False
        session.set_playback_position(data, position_ticks, played)
    except Exception:
        pass

    # Courtesy delay to allow a new session to take over if we are switching
    _time.sleep(1)

    # Only cleanup if this is still the active session
    if _is_session_active(my_id):
        _cleanup(session, client, config)


def play_other(session: EmbyHttpClient, data: dict, config: dict):
    """Switch content while the Oppo is already playing."""
    session.playstate = "Replay"
    params = session.process_data(data)
    try:
        item_info = session.get_item_info2(
            session.user_info["User"]["Id"], params["item_id"], params["media_source_id"]
        )
    except EmbyConnectionError as e:
        logger.error("Cannot fetch item info for replay: %s", e)
        session.playstate = "Playing"
        return

    movie = _translate_path(item_info.get("Path", ""), config.get("servers", []))
    parsed = OppoClient.parse_media_path(movie)
    container = item_info.get("Container", "")

    server_name = parsed["server"]
    folder = parsed["folder"]
    filename = parsed["filename"]

    actual_server = server_name
    if server_name.lower().startswith("volume"):
        logger.info("Detectado error común de Synology: '%s' no es un servidor, es un volumen.", server_name)
        folder = server_name + "/" + folder if folder else server_name
        actual_server = ""
        for s in config.get("servers", []):
            if s.get("Emby_Path") and s.get("Oppo_Path"):
                parts = s["Oppo_Path"].strip("/").split("/")
                if parts:
                    actual_server = parts[0]
                    break
        if not actual_server:
            try:
                from urllib.parse import urlparse
                emby_server_url = config.get("emby_server", "")
                actual_server = urlparse(emby_server_url).hostname or server_name
            except Exception:
                pass
        server_name = actual_server

    client = OppoClient(config["Oppo_IP"])
    try:
        devices = client.get_device_list()
    except Exception:
        devices = {}
    nfs = OppoClient.detect_nfs(server_name, devices, config.get("default_nfs", False))

    mount_folder = folder.lstrip("/")

    if nfs:
        client.login_nfs(server_name)
        client.mount_nfs(server_name, mount_folder)
    else:
        client.login_smb(server_name)
        client.mount_smb(server_name, mount_folder)

    if container == "bluray":
        client.check_folder_has_bdmv(filename, nfs)
    else:
        client.play_file(server_name, filename, "0", nfs)

    session.playnow(data)
    session.currentdata = data
    session.playstate = "Playing"
    logger.info("Replay started: %s", item_info.get("Name"))


def _wait_for_nfs(client, device_list, config):
    """Wait for the NFS server to appear in the Oppo's device list."""
    server_target = ""
    for s in config.get("servers", []):
        if s.get("Emby_Path") and s.get("Oppo_Path"):
             # Simple heuristic to find server name from config
             parts = s["Oppo_Path"].strip("/").split("/")
             if parts: server_target = parts[0]
    
    if not server_target:
        return

    logger.info("Waiting for NFS server: %s", server_target)
    for _ in range(10):
        for dev in device_list.get("devicelist", []):
            if dev.get("name", "").upper() == server_target.upper():
                logger.info("NFS server %s found", server_target)
                return
        _time.sleep(2)
        device_list = client.get_device_list()


def _notify_user(session, params, text, config, timeout_ms=3500):
    try:
        session.send_user_message(params.get("ControllingUserId", ""), text, timeout_ms)
    except Exception:
        pass


def _cleanup(session: EmbyHttpClient, client: OppoClient, config: dict):
    """Closes Oppo session and resets Emby state."""
    
    # ── HARDWARE PROTECTION ──
    # Before doing anything, check if the Oppo is already playing something else
    try:
        info = client.get_global_info()
        if '"is_video_playing":true' in info:
            logger.info("Oppo ya está reproduciendo contenido nuevo. Cancelando limpieza de standby.")
            return
    except Exception:
        pass

    session.playstate = "Free"
    session.last_cleanup_time = _time.time()
    
    # AV Control - Restore input OR Power Off (Primary attempt)
    # CRITICAL: Skip power off/AV restore if we are just switching content (Replay)
    if config.get("AV") and session.playstate != "Replay":
        try:
            from .av_control import av_set_input, av_power_off
            original_input = config.get("_original_av_input")
            if original_input:
                logger.info("Final de película: Restaurando entrada AV original...")
                av_set_input(config, original_input)
                config["_original_av_input"] = None
            elif not config.get("AV_Always_ON"):
                logger.info("Final de película: Apagando receptor AV...")
                av_power_off(config)
        except Exception as e:
            logger.error("Error al restaurar AV en cleanup: %s", e)

    # Oppo Standby
    # CRITICAL: Skip standby if we are just switching content (Replay)
    if not config.get("Always_ON") and session.playstate != "Replay":
        try:
            logger.info("Final de película: Poniendo Oppo en Standby...")
            client.send_remote_key("POW")
        except Exception:
            pass

    # Slow operations last
    try:
        client.unmount()
        client.sign_out()
    except Exception:
        pass

    session.server = ""
    session.playedtitle = ""
    session.played_item_id = ""
    session.played_image_tag = ""
    session.folder = ""
    session.filename = ""
