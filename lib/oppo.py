"""
Oppo UDP-203 API Client — Xnoppo
Wraps all HTTP calls to the Oppo player's REST API on port 436.
"""

import json
import logging
import socket
import time
import urllib.parse

import requests

logger = logging.getLogger(__name__)
OPPO_PORT = 436


class OppoConnectionError(Exception):
    pass


class OppoClient:
    """Client for the Oppo UDP-203 HTTP control API."""

    def __init__(self, ip: str, connection_timeout: int = 10,
                 mount_timeout: int = 60, play_timeout: int = 60):
        self.ip = ip
        self.connection_timeout = connection_timeout
        self.mount_timeout = mount_timeout
        self.play_timeout = play_timeout
        self._session = requests.Session()
        self._base = f"http://{ip}:{OPPO_PORT}"

    def _get(self, endpoint: str, timeout: int | None = None) -> str:
        url = self._base + endpoint
        logger.debug("Oppo GET: %s", url)
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                resp = self._session.get(url, timeout=timeout or self.play_timeout)
                resp.raise_for_status()
                logger.debug("Oppo response: %s", resp.text[:200])
                return resp.text
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                if attempt == max_attempts - 1:
                    logger.error("Oppo request failed after %d attempts: %s", max_attempts, e)
                    return "{}" # Return empty JSON string to avoid crashes
                logger.warning("Oppo connection issue (attempt %d/%d), retrying in 1s...", attempt + 1, max_attempts)
                time.sleep(1)
        return "{}"

    # ── Connection ────────────────────────────────────────────────────────

    def check_connection(self) -> int:
        """Return 0 if Oppo is reachable, 1 if not (after retries)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((self.ip, OPPO_PORT))
        retries = 0
        while result != 0 and retries < self.connection_timeout:
            time.sleep(1)
            retries += 1
            self.send_notify_remote()
            result = sock.connect_ex((self.ip, OPPO_PORT))
        sock.close()
        if result != 0:
            logger.warning("Oppo not reachable after %d retries", retries)
            return 1
        logger.info("Oppo connection established")
        return 0

    def send_notify_remote(self):
        """Wake Oppo via UDP broadcast."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b"NOTIFY OREMOTE LOGIN", (self.ip, 7624))
        except OSError as e:
            logger.debug("UDP notify failed: %s", e)

    # ── Oppo API calls ────────────────────────────────────────────────────

    def get_firmware_version(self) -> str:
        return self._get("/getmainfirmwareversion")

    def get_setup_menu(self) -> str:
        return self._get("/getsetupmenu")

    def get_global_info(self) -> str:
        return self._get("/getglobalinfo")

    def get_playing_time(self) -> dict:
        raw = self._get("/getplayingtime")
        return json.loads(raw)

    def get_device_list(self) -> dict:
        raw = self._get("/getdevicelist")
        return json.loads(raw)

    def sign_in(self, app_ip: str = "127.0.0.1") -> str:
        payload = urllib.parse.quote(
            f'{{"appIconType":1,"appIpAddress":"{app_ip}"}}'
        )
        return self._get(f"/signin?{payload}")

    def send_remote_key(self, key: str) -> str:
        payload = urllib.parse.quote(f'{{"key":"{key}"}}')
        return self._get(f"/sendremotekey?{payload}")

    # ── Mount / Login ──────────────────────────────────────────────────────

    def login_smb(self, server: str) -> dict:
        payload = urllib.parse.quote(f'{{"serverName":"{server}"}}')
        raw = self._get(f"/loginSambaWithOutID?{payload}")
        return json.loads(raw)

    def login_nfs(self, server: str) -> dict:
        payload = urllib.parse.quote(f'{{"serverName":"{server}"}}')
        raw = self._get(f"/loginNfsServer?{payload}")
        return json.loads(raw)

    def mount_smb(self, server: str, folder: str,
                  username: str = "", password: str = "") -> dict:
        q = urllib.parse.quote(folder)
        endpoint = (
            f'/mountSharedFolder?{{"server":"{server}",'
            f'"bWithID":0,"folder":"{q}",'
            f'"userName":"{username}","password":"{password}","bRememberID":0}}'
        )
        try:
            raw = self._get(endpoint, timeout=self.mount_timeout)
        except requests.Timeout:
            return {"success": False, "retInfo": "Timeout mounting SMB"}
        return json.loads(raw)

    def mount_nfs(self, server: str, folder: str) -> dict:
        q = urllib.parse.quote(folder)
        endpoint = f'/mountNfsSharedFolder?{{"server":"{server}","folder":"{q}"}}'
        try:
            raw = self._get(endpoint, timeout=self.mount_timeout)
        except requests.Timeout:
            return {"success": False, "retInfo": "Timeout mounting NFS"}
        if raw == "{}":
            return {"success": True, "retInfo": ""}
        return json.loads(raw)

    def unmount(self) -> str:
        """Unmount via telnet (Oppo's umount command)."""
        try:
            import telnetlib
            session = telnetlib.Telnet(self.ip, 23, timeout=10)
            session.read_until(b"login: ", 10)
            session.write(b"root\n")
            session.write(b"umount /mnt/cifs1\n")
            session.write(b"exit\n")
            session.read_all()
            return "OK"
        except Exception as e:
            logger.warning("Unmount failed: %s", e)
            return "ERROR"

    # ── Playback ──────────────────────────────────────────────────────────

    def play_file(self, server: str, filename: str,
                  index: str = "0", nfs: bool = False) -> dict:
        mount_path = "nfs1" if nfs else "cifs1"
        inner = (
            f'"path":"/mnt/{mount_path}/{filename}",'
            f'"index":{index},"type":1,"appDeviceType":2,'
            f'"extraNetPath":"{server}","playMode":0'
        )
        endpoint = f"/playnormalfile?{{{urllib.parse.quote(inner)}}}"
        try:
            raw = self._get(endpoint, timeout=self.play_timeout)
        except requests.Timeout:
            return {"success": False, "retInfo": "Timeout playing file"}
        return json.loads(raw)

    def check_folder_has_bdmv(self, folder: str, nfs: bool = False) -> dict:
        mount_path = "nfs1" if nfs else "cifs1"
        q = urllib.parse.quote(folder)
        endpoint = f'/checkfolderhasBDMV?{{"folderpath":"/mnt/{mount_path}/{q}"}}'
        try:
            raw = self._get(endpoint, timeout=self.play_timeout)
        except requests.Timeout:
            return {"success": False, "retInfo": "Timeout"}
        return json.loads(raw)

    def set_play_time(self, ticks: int):
        secs = ticks / 10_000_000
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        endpoint = f'/setplaytime?{{"h":{h},"m":{m},"s":{s}}}'
        return self._get(endpoint)

    def set_audio_track(self, index: int) -> str:
        return self._get(f'/setaudiomenulist?{{"cur_index":{index}}}')

    def set_subtitle_track(self, index: int) -> str:
        return self._get(f'/setsubttmenulist?{{"cur_index":{index}}}')

    def get_subtitle_track(self) -> int:
        raw = self._get("/getsubtitlemenulist?")
        try:
            data = json.loads(raw)
            for sub in data.get("subtitle_list", []):
                if sub.get("selected"):
                    return sub["index"]
        except (json.JSONDecodeError, KeyError):
            pass
        return 0

    def get_file_list(self, folder: str, nfs: bool = False) -> list:
        mount_path = "nfs1" if nfs else "cifs1"
        # Ensure path starts with / and doesn't end with /
        clean_folder = "/" + folder.strip("/") if folder.strip("/") else ""
        q = urllib.parse.quote(clean_folder)
        endpoint = f'/getfilelist?{{"path":"/mnt/{mount_path}{q}","fileType":1,"mediaType":3,"flag":1}}'
        resp = self._session.get(self._base + endpoint)
        return self._parse_file_list(resp.content)

    def get_smb_share_list(self) -> list:
        resp = self._session.get(self._base + "/getSambaShareFolderlist")
        return self._parse_file_list(resp.content)

    def get_nfs_share_list(self) -> list:
        resp = self._session.get(self._base + "/getNfsShareFolderlist")
        return self._parse_file_list(resp.content)

    def _parse_file_list(self, raw: bytes) -> list:
        """Robustly parse Oppo's binary file list responses."""
        files = [{"Id": 0, "Foldername": ".."}]
        idx = 1
        # The Oppo API returns data separated by \x01.
        for part in raw.split(b"\x01"):
            if not part or b"\x02" in part or b"\x03" in part:
                continue
            
            # Find the last control character/null byte position to isolate the name
            # Oppo often puts binary headers/junk before the actual string.
            last_junk = -1
            for i, b in enumerate(part):
                if b < 32 or b == 127:
                    last_junk = i
            
            # Take everything after the last junk character
            name_bytes = part[last_junk + 1:] if last_junk != -1 else part
            
            # Strip any remaining non-printable characters
            cleaned = b"".join(bytes([b]) for b in name_bytes if (b >= 32 and b != 127) or b > 159)
            
            try:
                name = cleaned.decode("utf-8").strip()
                # Ignore specific technical strings
                if name and name.upper() != "FLAG":
                    # Ensure it contains at least one alphanumeric character
                    import re
                    if re.search(r'[a-zA-Z0-9\u00C0-\u017F]', name):
                        files.append({"Id": idx, "Foldername": name})
                        idx += 1
            except UnicodeDecodeError:
                pass
        return files

    # ── Path parsing ──────────────────────────────────────────────────────

    @staticmethod
    def parse_media_path(movie: str) -> dict[str, str]:
        """
        Parse a UNC-style network path into server / folder / filename.
        Handles:
          - '/NAS/movies/film.mkv'
          - 'nfs://192.168.1.17/volume1/Plex/film.iso'
        """
        movie = movie.replace("\\\\", "\\").replace("\\", "/")
        if "://" in movie:
            movie = movie.split("://", 1)[1]
        
        parts = [p for p in movie.split("/") if p]
        if len(parts) < 1:
            return {"server": "", "folder": "", "filename": ""}
        
        server = parts[0]
        filename = parts[-1] if len(parts) > 1 else ""
        folder = "/".join(parts[1:-1]) if len(parts) > 2 else ""
        return {"server": server, "folder": folder, "filename": filename}

    @staticmethod
    def detect_nfs(server: str, device_list: dict, default_nfs: bool = False) -> bool:
        for device in device_list.get("devicelist", []):
            if device.get("name", "").upper() == server.upper():
                return device.get("sub_type") == "nfs"
        return default_nfs
