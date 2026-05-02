"""
API Routes — JSON API endpoints for the Xnoppo web interface.
Handles config CRUD, status, version checking, device testing, and remote control.
"""

import json
import logging
from pathlib import Path

import psutil
from flask import Blueprint, jsonify, request, current_app

from config import XnoppoConfig

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


# ─── Configuration ────────────────────────────────────────────────────────────

@api_bp.route("/config", methods=["GET"])
def get_config():
    """Return the current configuration."""
    config = current_app.config["XNOPPO"]
    # Sanitize: don't expose password in GET
    data = config.to_dict()
    return jsonify(data)


@api_bp.route("/config", methods=["POST"])
def save_config():
    """Save updated configuration from the frontend."""
    config = current_app.config["XNOPPO"]
    new_data = request.get_json()
    if not new_data:
        return jsonify({"error": "No data provided"}), 400

    if "MonitoredDevice" in new_data:
        logger.info("Configuración actualizada: MonitoredDevice -> '%s'", new_data["MonitoredDevice"])

    config.update(new_data)
    config.save()

    # Reconfigure logging level in case it changed
    try:
        from app import setup_logging
        setup_logging(config)
    except Exception:
        pass

    # If WebSocket thread is not running, try to start it now
    if not config.get_ws_client():
        try:
            from lib.ws_launcher import start_ws_thread
            start_ws_thread(config)
        except Exception:
            pass

    return jsonify({"status": "ok", "message": "Configuration saved"})


# ─── Status ───────────────────────────────────────────────────────────────────

@api_bp.route("/state", methods=["GET"])
def get_state():
    """Return current playback state and system metrics."""
    config = current_app.config["XNOPPO"]
    status = {
        "Version": config.get_version(),
        "cpu_perc": psutil.cpu_percent(),
        "mem_perc": psutil.virtual_memory().percent,
        "Playstate": "Not_Connected",
        "playedtitle": "",
        "server": "",
        "folder": "",
        "filename": "",
        "CurrentData": "",
    }

    # Try to get live playback state from WebSocket session
    ws_client = config.get_ws_client()
    if ws_client:
        status["Playstate"] = "Conectado" 
        if hasattr(ws_client, "EmbySession") and ws_client.EmbySession:
            try:
                session = ws_client.EmbySession
                status["Playstate"] = session.playstate
                status["playedtitle"] = session.playedtitle or ""
                status["server"] = session.server or ""
                status["folder"] = session.folder or ""
                status["filename"] = session.filename or ""
                status["CurrentData"] = session.currentdata or ""
                
                # If we don't have a stored ID, try to find it in the current session list
                item_id = session.played_item_id
                image_tag = session.played_image_tag
                
                if not item_id:
                    # Look for our monitored device in the sessions
                    monitored = str(config.get("MonitoredDevice", "")).strip().lower()
                    if monitored:
                        all_sessions = session.get_sessions()
                        for s in (all_sessions if isinstance(all_sessions, list) else []):
                            s_id = str(s.get("DeviceId", "")).strip().lower()
                            s_name = str(s.get("DeviceName", "")).strip().lower()
                            if s_id == monitored or monitored in s_name or s_name in monitored:
                                now_playing = s.get("NowPlayingItem")
                                if now_playing:
                                    item_id = now_playing.get("Id")
                                    image_tag = now_playing.get("ImageTags", {}).get("Primary", "")
                                    break

                if item_id:
                    emby_server = config.get("emby_server", "").rstrip("/")
                    tag_param = f"?tag={image_tag}&quality=90" if image_tag else ""
                    status["poster_url"] = f"{emby_server}/emby/Items/{item_id}/Images/Primary{tag_param}"
                else:
                    status["poster_url"] = None
            except Exception as e:
                logger.error("Error updating status poster: %s", e)
    else:
        status["Playstate"] = "Sin conexión"

    return jsonify(status)


# ─── Version ──────────────────────────────────────────────────────────────────

@api_bp.route("/version", methods=["GET"])
def check_version():
    """Check if a new version is available on GitHub."""
    import requests as req
    config = current_app.config["XNOPPO"]

    try:
        url = "https://raw.githubusercontent.com/siberian-git/Xnoppo/main/versions/version.js"
        resp = req.get(url, timeout=10)
        resp.raise_for_status()
        version_data = resp.json()

        if config.get("check_beta"):
            latest = version_data.get("beta_version", "0")
            latest_file = version_data.get("beta_version_file", "")
        else:
            latest = version_data.get("curr_version", "0")
            latest_file = version_data.get("curr_version_file", "")

        current = config.get_version()
        return jsonify({
            "version": latest,
            "file": latest_file,
            "new_version": current < latest,
            "current_version": current,
        })
    except Exception as e:
        logger.error("Version check failed: %s", e)
        return jsonify({"error": str(e)}), 500


# ─── Device Testing ──────────────────────────────────────────────────────────

@api_bp.route("/test/emby", methods=["POST"])
def test_emby():
    """Test Emby server connectivity. Falls back to saved config if password is not provided."""
    data = request.get_json() or {}
    config = current_app.config["XNOPPO"]
    
    # Merge: request data takes precedence, saved config fills any blanks
    merged = config.to_dict().copy()
    merged.update({k: v for k, v in data.items() if v})  # only overwrite with non-empty values
    
    try:
        from lib.emby_http import EmbyHttpClient
        session = EmbyHttpClient(merged)
        user_info = session.user_info
        if user_info and user_info.get("SessionInfo", {}).get("Id"):
            return jsonify({"status": "OK", "user": user_info.get("User", {}).get("Name", "")})
        else:
            return jsonify({"status": "FAILED"}), 400
    except Exception as e:
        logger.error("Emby test failed: %s", e)
        return jsonify({"status": "FAILED", "error": str(e)}), 400


@api_bp.route("/test/oppo", methods=["POST"])
def test_oppo():
    """Test Oppo player connectivity."""
    data = request.get_json() or {}
    try:
        from lib.oppo import OppoClient
        client = OppoClient(data.get("Oppo_IP", ""), data.get("timeout_oppo_conection", 10))
        result = client.check_connection()
        if result == 0:
            return jsonify({"status": "OK"})
        else:
            return jsonify({"status": "FAILED"}), 400
    except Exception as e:
        logger.error("Oppo test failed: %s", e)
        return jsonify({"status": "FAILED", "error": str(e)}), 400


@api_bp.route("/test/oppo_path", methods=["POST"])
def test_oppo_path():
    """Test mounting a specific path on the Oppo."""
    data = request.get_json() or {}
    config = current_app.config["XNOPPO"]
    oppo_path = data.get("Oppo_Path", "")
    if not oppo_path:
        return jsonify({"error": "No path provided"}), 400
        
    try:
        from lib.oppo import OppoClient
        client = OppoClient(config["Oppo_IP"])
        if client.check_connection() != 0:
            return jsonify({"error": "No se puede conectar al Oppo"}), 400
            
        parsed = OppoClient.parse_media_path(oppo_path + "/dummy")
        server_name = parsed["server"]
        folder = parsed["folder"]
        
        devices = client.get_device_list()
        nfs = OppoClient.detect_nfs(server_name, devices, config.get("default_nfs", False))
        
        if nfs:
            client.login_nfs(server_name)
            mount_result = client.mount_nfs(server_name, folder)
        else:
            client.login_smb(server_name)
            mount_result = client.mount_smb(server_name, folder)
            
        if mount_result.get("success"):
            client.unmount()
            return jsonify({"status": "OK", "message": "Ruta montada correctamente", "type": "NFS" if nfs else "SMB"})
        else:
            return jsonify({"error": mount_result.get("retInfo", "Error de montaje")}), 400
    except Exception as e:
        logger.error("Test Oppo path failed: %s", e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/oppo/shares", methods=["GET"])
def get_oppo_shares():
    """Get list of network servers/shares visible to the Oppo."""
    config = current_app.config["XNOPPO"]
    try:
        from lib.oppo import OppoClient
        client = OppoClient(config["Oppo_IP"])
        if client.check_connection() != 0:
            return jsonify({"error": "No se puede conectar al Oppo"}), 400
            
        devices = client.get_device_list()
        shares = devices.get("devicelist", []) if isinstance(devices, dict) else []
        return jsonify({"shares": shares})
    except Exception as e:
        logger.error("Get Oppo shares failed: %s", e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/oppo/shares/folders", methods=["POST"])
def get_oppo_share_folders():
    """Get list of shared folders for a specific server via the Oppo."""
    data = request.get_json() or {}
    config = current_app.config["XNOPPO"]
    server_name = data.get("server", "")
    protocol = data.get("protocol", "smb")  # "smb" or "nfs"
    if not server_name:
        return jsonify({"error": "No server specified"}), 400
    try:
        from lib.oppo import OppoClient
        client = OppoClient(config["Oppo_IP"])
        if client.check_connection() != 0:
            return jsonify({"error": "No se puede conectar al Oppo"}), 400
        
        if protocol == "nfs":
            client.login_nfs(server_name)
            folders = client.get_nfs_share_list()
        else:
            client.login_smb(server_name)
            folders = client.get_smb_share_list()
        
        # Filter out the ".." entry
        folder_names = [f.get("Foldername", "") for f in folders if f.get("Foldername") and f.get("Foldername") != ".."]
        return jsonify({"folders": folder_names, "server": server_name, "protocol": protocol})
    except Exception as e:
        logger.error("Get share folders failed: %s", e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/oppo/browse", methods=["POST"])
def browse_oppo_folder():
    """Mount a share and list subdirectories for deep folder navigation."""
    data = request.get_json() or {}
    config = current_app.config["XNOPPO"]
    server_name = data.get("server", "")
    share = data.get("share", "")          # top-level share to mount (e.g. "Video")
    subpath = data.get("subpath", "")       # path inside the share (e.g. "/Plex/Library")
    protocol = data.get("protocol", "smb")
    if not server_name or not share:
        return jsonify({"error": "server and share are required"}), 400
    try:
        from lib.oppo import OppoClient
        client = OppoClient(config["Oppo_IP"])
        if client.check_connection() != 0:
            return jsonify({"error": "No se puede conectar al Oppo"}), 400

        nfs = protocol == "nfs"
        # Login + mount the share
        if nfs:
            client.login_nfs(server_name)
            client.mount_nfs(server_name, share)
        else:
            client.login_smb(server_name)
            client.mount_smb(server_name, share)

        # Browse inside the mounted share
        browse_path = "/" + subpath.strip("/") if subpath else "/"
        items = client.get_file_list(browse_path, nfs)

        # Separate folders from files (folders don't have extensions typically)
        folders = []
        files = []
        for item in items:
            name = item.get("Foldername", "")
            if not name or name == "..":
                continue
            # Heuristic: if it has a media extension, it's a file
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            media_exts = {"mkv","mp4","avi","m4v","ts","iso","bdmv","mpls","m2ts","wmv","mov","flv","webm"}
            if ext in media_exts:
                files.append(name)
            else:
                folders.append(name)

        return jsonify({
            "folders": folders,
            "files": files,
            "server": server_name,
            "share": share,
            "subpath": subpath,
            "protocol": protocol
        })
    except Exception as e:
        logger.error("Browse Oppo folder failed: %s", e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/test/av_<action>", methods=["POST"])
def test_av(action):
    """Test AV receiver functions."""
    data = request.get_json() or {}
    try:
        from lib.av_control import av_test, av_check_power, av_change_hdmi, av_power_off, get_hdmi_list
        res = "OK"
        if action == "conn":
            res = av_test(data)
        elif action == "on":
            res = av_check_power(data)
        elif action == "hdmi":
            res = av_change_hdmi(data)
        elif action == "off":
            res = av_power_off(data)
        elif action == "hdmi_list":
            res = get_hdmi_list(data)
            if res is None:
                return jsonify({"error": "No soportado"}), 400
        else:
            return jsonify({"error": "Invalid action"}), 400
        return jsonify({"status": "OK", "result": res})
    except Exception as e:
        logger.error("AV test %s failed: %s", action, e)
        return jsonify({"status": "FAILED", "error": str(e)}), 400


@api_bp.route("/emby/libraries", methods=["POST"])
def fetch_libraries():
    """Fetch libraries from Emby and update config."""
    config = current_app.config["XNOPPO"]
    try:
        from lib.emby_http import EmbyHttpClient
        session = EmbyHttpClient(config.to_dict())
        user_info = session.user_info
        if not user_info:
            return jsonify({"error": "Not authenticated"}), 401
            
        user_id = user_info["User"]["Id"]
        items = session.get_user_views(user_id)
        
        current_lib = config.get("Libraries", [])
        lib_arr = []
        
        for item in items:
            lib = {
                "Name": item.get("Name"),
                "Id": item.get("Id"),
                "Active": True
            }
            # Preserve existing 'Active' state if present
            for c_l in current_lib:
                if c_l.get("Id") == item.get("Id"):
                    lib["Active"] = c_l.get("Active", True)
                    break
            lib_arr.append(lib)
            
        config["Libraries"] = lib_arr
        config.save()
        return jsonify({"Libraries": lib_arr})
    except Exception as e:
        logger.error("Fetch libraries failed: %s", e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/emby/paths", methods=["GET"])
def fetch_emby_paths():
    """Fetch physical paths configured in Emby libraries."""
    config = current_app.config["XNOPPO"]
    try:
        from lib.emby_http import EmbyHttpClient
        session = EmbyHttpClient(config.to_dict())
        folders = session.get_emby_selectablefolders()
        paths = []
        if isinstance(folders, list):
            for f in folders:
                for sub in f.get("SubFolders", []):
                    p = sub.get("Path")
                    if p and p not in paths:
                        paths.append(p)
        return jsonify({"paths": paths})
    except Exception as e:
        logger.error("Fetch paths failed: %s", e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/emby/devices", methods=["GET"])
def fetch_emby_devices():
    """Fetch devices from Emby server."""
    config = current_app.config["XNOPPO"]
    try:
        from lib.emby_http import EmbyHttpClient
        session = EmbyHttpClient(config.to_dict())
        devices = session.get_emby_devices()
        items = devices.get("Items", []) if isinstance(devices, dict) else devices
        return jsonify({"devices": items})
    except Exception as e:
        logger.error("Fetch devices failed: %s", e)
        return jsonify({"error": str(e)}), 500


# ─── Remote Control ──────────────────────────────────────────────────────────

@api_bp.route("/remote/key", methods=["POST"])
def send_key():
    """Send a remote control key to the Oppo player."""
    data = request.get_json() or {}
    key = data.get("key", "")
    if not key:
        return jsonify({"error": "No key specified"}), 400

    config = current_app.config["XNOPPO"]
    try:
        from lib.oppo import OppoClient
        client = OppoClient(config["Oppo_IP"], config.get("timeout_oppo_conection", 10))
        
        # Try to wake/check connection before sending key
        if client.check_connection() == 0:
            client.send_remote_key(key)
            return jsonify({"status": "ok"})
        else:
            return jsonify({"error": "Oppo no responde. ¿Está encendido?"}), 503
    except Exception as e:
        logger.error("Remote key failed: %s", e)
        return jsonify({"error": str(e)}), 500


# ─── System ───────────────────────────────────────────────────────────────────

@api_bp.route("/news/4k", methods=["GET"])
def get_4k_news():
    """Scraper robusto de estrenos 4K usando Blu-ray.com (Motor Blindado)"""
    import requests
    from bs4 import BeautifulSoup
    
    url = "https://www.blu-ray.com/movies/movies.php?show=comingsoon&sortby=releasedate&format=4K"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    products = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # En Blu-ray.com los items están en tablas o celdas específicas
        items = soup.select("table[width='100%'] table tr td[align='center']")[:12] # Top 12
        
        for item in items:
            title_el = item.select_one("a[title]")
            img_el = item.select_one("img")
            
            if title_el and img_el:
                title = title_el.get("title", "").replace(" 4K Blu-ray", "").strip()
                img_url = img_el.get("src", "")
                
                # Limpiar URL de imagen (Blu-ray.com usa miniaturas, buscamos la grande)
                if "/thumbs/" in img_url:
                    img_url = img_url.replace("/thumbs/", "/images/").replace("_front", "")
                
                if not img_url.startswith("http"):
                    img_url = f"https://www.blu-ray.com{img_url}"
                
                products.append({
                    "title": title,
                    "image_url": f"/static/img/cache/{local_filename}",
                    "remote_url": img_url
                })
            
        if not products:
            logger.warning("Scraper found no products in DVDLand, using internal fallbacks")
            # Fallback logic...
            
        cache_file.write_text(json.dumps(products, indent=2), encoding="utf-8")
        return jsonify(products)
    except Exception as e:
        logger.error("Fetch 4K news failed: %s", e)
        return jsonify([])


@api_bp.route("/restart", methods=["POST"])
def restart():
    """Request application restart."""
    import os
    logger.info("Restart requested via API — Exiting process for Docker restart")
    # In Docker, exiting will trigger a restart if 'restart: always' is set
    os._exit(0)


@api_bp.route("/log", methods=["GET"])
def get_log():
    """Return the application log file contents."""
    base_dir = current_app.config["BASE_DIR"]
    log_file = base_dir / "xnoppo.log"
    if log_file.exists():
        content = log_file.read_text(encoding="utf-8", errors="replace")
        # Return last 500 lines
        lines = content.splitlines()[-500:]
        return "\n".join(lines), 200, {"Content-Type": "text/plain; charset=utf-8"}
    return "No log file found", 404
