"""
Emby HTTP Client — Xnoppo
Clean rewrite of Emby_http.py.
"""

import hashlib
import json
import logging
import urllib.parse

import requests

logger = logging.getLogger(__name__)

CLIENT_VERSION = "3.00"
CLIENT_NAME = "Emby Xnoppo"
DEVICE_ID = "Xnoppo"


class EmbyAuthError(Exception):
    pass


class EmbyConnectionError(Exception):
    pass


class EmbyHttpClient:
    """HTTP client for the Emby media server API."""

    def __init__(self, config: dict):
        self.config = config
        self._session = requests.Session()
        self.user_info: dict = {}
        self.PlaySessionId: str = ""
        self.playstate: str = "Free"
        self.playedtitle: str = ""
        self.played_item_id: str = ""
        self.played_image_tag: str = ""
        self.server: str = ""
        self.folder: str = ""
        self.filename: str = ""
        self.currentdata: dict = {}
        self.lang: dict = {}

        self.user_info = self._authenticate()
        logger.info("EmbyHttpClient authenticated as %s", config.get("user_name"))

    # ── Auth & Headers ─────────────────────────────────────────────────────

    def _get_headers(self, include_token: bool = True) -> dict:
        auth = (
            f'MediaBrowser Client="{CLIENT_NAME}",'
            f'Device="{DEVICE_ID}",'
            f'DeviceId="{DEVICE_ID}",'
            f'Version="{CLIENT_VERSION}"'
        )
        if include_token and self.user_info.get("AccessToken"):
            auth += f',UserId="{self.user_info["User"]["Id"]}"'
        headers = {
            "X-Emby-Authorization": auth,
            "Accept-Charset": "UTF-8,*",
            "Accept-Encoding": "gzip",
        }
        if include_token and self.user_info.get("AccessToken"):
            headers["X-MediaBrowser-Token"] = self.user_info["AccessToken"]
        return headers

    def _authenticate(self) -> dict:
        server = self.config.get("emby_server", "")
        url = f"{server}/Users/AuthenticateByName?format=json"
        password = self.config.get("user_password", "")
        pwd_sha = hashlib.sha1(password.encode()).hexdigest()
        data = {
            "username": self.config.get("user_name", ""),
            "password": pwd_sha,
            "pw": password,
        }
        try:
            resp = self._session.post(url, data=data, headers=self._get_headers(False), timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            raise EmbyAuthError(f"Authentication failed: {e}") from e
        except requests.RequestException as e:
            raise EmbyConnectionError(f"Cannot reach Emby server: {e}") from e

    # ── Generic requests ────────────────────────────────────────────────────

    def _get(self, url: str) -> dict:
        server = self.config.get("emby_server", "")
        url = url.replace("{server}", server)
        try:
            response = self._session.get(url, headers=self._get_headers(), timeout=5)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}

    def _post(self, url: str, data: dict) -> requests.Response:
        server = self.config.get("emby_server", "")
        url = url.replace("{server}", server)
        logger.debug("Emby POST: %s", url)
        try:
            resp = self._session.post(url, data=data, headers=self._get_headers(), timeout=15)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.error("Emby POST failed %s: %s", url, e)
            raise EmbyConnectionError(str(e)) from e

    def get_sessions(self):
        """Fetch all active sessions from Emby server."""
        return self._get("{server}/emby/Sessions")

    def get_session_details(self, session_id: str):
        return self._get("{server}/emby/Sessions/" + str(session_id) + "?format=json")

    # ── Session capabilities ────────────────────────────────────────────────

    def set_capabilities(self):
        url = "{server}/emby/Sessions/Capabilities/Full?format=json"
        data = {
            "SupportsMediaControl": True,
            "PlayableMediaTypes": ["Video", "Audio"],
            "SupportedCommands": [
                "Play", "Playstate", "MoveUp", "MoveDown", "MoveLeft", "MoveRight",
                "Select", "Back", "GoHome", "PageUp", "PageDown", "ToggleFullscreen",
                "ToggleOsdMenu", "VolumeUp", "VolumeDown", "ToggleMute", "SetVolume",
                "SetAudioStreamIndex", "SetSubtitleStreamIndex", "SetRepeatMode",
                "Mute", "Unmute", "PlayNext", "PlayMediaSource",
            ],
            "DeviceProfile": {},
        }
        self._post(url, data)

    # ── Now playing reports ─────────────────────────────────────────────────

    def process_data(self, data: dict) -> dict:
        item_ids = data.get("ItemIds", [])
        if isinstance(item_ids, list) and item_ids:
            item_id = item_ids[0]
        else:
            item_id = item_ids
        start_ticks = data.get("StartPositionTicks", -1)
        if start_ticks < 0:
            info = self.get_item_info(data.get("ControllingUserId", ""), item_id)
            start_ticks = info.get("UserData", {}).get("PlaybackPositionTicks", 0)
        return {
            "item_id": item_id,
            "auto_resume": start_ticks,
            "media_source_id": data.get("MediaSourceId", ""),
            "subtitle_stream_index": data.get("SubtitleStreamIndex", -1),
            "audio_stream_index": data.get("AudioStreamIndex", 1),
            "ControllingUserId": data.get("ControllingUserId", ""),
            "Session_id": data.get("SessionID"),
            "DeviceName": data.get("DeviceName", ""),
            "Device_Id": data.get("Device_Id", ""),
        }

    def playnow(self, data: dict):
        session_info = self.user_info["SessionInfo"]
        params = self.process_data(data)
        pi_url = f"{{server}}/Items/{params['item_id']}/PlaybackInfo?format=json"
        pi = self._get(pi_url)
        self.PlaySessionId = pi.get("PlaySessionId", "")
        url = "{server}/emby/Sessions/Playing/?format=json"
        payload = {
            "CanSeek": True, "ItemId": params["item_id"],
            "SessionId": session_info["Id"],
            "MediaSourceId": params["media_source_id"],
            "AudioStreamIndex": params["audio_stream_index"],
            "SubtitleStreamIndex": params["subtitle_stream_index"],
            "IsPaused": False, "IsMuted": False, "PositionTicks": 0,
            "PlayMethod": "DirectPlay", "PlaySessionId": self.PlaySessionId,
            "RepeatMode": "RepeatNone",
        }
        self._post(url, payload)

    def playing_progress(self, data: dict, position: int, total: int,
                         paused: bool, muted: bool):
        params = self.process_data(data)
        session_info = self.user_info["SessionInfo"]
        payload = {
            "CanSeek": True, "ItemId": params["item_id"],
            "SessionId": session_info["Id"],
            "MediaSourceId": params["media_source_id"],
            "AudioStreamIndex": params["audio_stream_index"],
            "SubtitleStreamIndex": params["subtitle_stream_index"],
            "IsPaused": paused, "IsMuted": muted,
            "PositionTicks": position, "RunTimeTicks": total,
            "PlayMethod": "DirectPlay", "PlaySessionId": self.PlaySessionId,
            "RepeatMode": "RepeatNone", "EventName": "timeupdate",
        }
        self._post("{server}/emby/Sessions/Playing/Progress?format=json", payload)

    def playing_stopped(self, data: dict, position: int, paused: bool, muted: bool):
        params = self.process_data(data)
        session_info = self.user_info["SessionInfo"]
        payload = {
            "CanSeek": True, "ItemId": params["item_id"],
            "SessionId": session_info["Id"],
            "MediaSourceId": params["media_source_id"],
            "AudioStreamIndex": params["audio_stream_index"],
            "SubtitleStreamIndex": params["subtitle_stream_index"],
            "IsPaused": paused, "IsMuted": muted,
            "PositionTicks": position,
            "PlayMethod": "DirectPlay", "PlaySessionId": self.PlaySessionId,
            "RepeatMode": "RepeatNone", "EventName": "timeupdate",
        }
        self._post("{server}/emby/Sessions/Playing/Stopped?format=json", payload)

    def set_playback_position(self, data: dict, position: int, played: bool):
        params = self.process_data(data)
        user_id = self.user_info["User"]["Id"]
        url = f"{{server}}/Users/{user_id}/Items/{params['item_id']}/UserData?format=json"
        self._post(url, {"played": played, "PlaybackPositionTicks": position})

    def playback_stop(self, session_id: str):
        url = f"{{server}}/emby/Sessions/{str(session_id)}/Command/Stop?format=json"
        self._post(url, {})

    def send_message(self, session_id: str, text: str, timeout_ms: int = 3500):
        url = (f"{{server}}/emby/Sessions/{str(session_id)}/Message"
               f"?Text={urllib.parse.quote(str(text))}&Header=Notification&TimeoutMs={str(timeout_ms)}")
        self._post(url, {})

    def send_user_message(self, user_id: str, text: str, timeout_ms: int = 3500):
        sessions = self._get(f"{{server}}/emby/Sessions?ControllableByUserId={user_id}")
        for s in sessions if isinstance(sessions, list) else []:
            try:
                self.send_message(s["Id"], text, timeout_ms)
            except EmbyConnectionError:
                pass

    # ── Item info ────────────────────────────────────────────────────────────

    def get_item_info(self, user_id: str, item_id: str) -> dict:
        return self._get("{server}/emby/Users/" + str(user_id) + "/Items/" + str(item_id))

    def get_item_info2(self, user_id: str, item_id: str, media_source_id: str) -> dict:
        data = self._get("{server}/emby/Users/" + str(user_id) + "/Items/" + str(item_id))
        for source in data.get("MediaSources", []):
            if source.get("Id") == media_source_id:
                return source
        return data

    def get_user_views(self, user_id: str) -> list:
        data = self._get("{server}/emby/Users/" + str(user_id) + "/Views?IncludeExternalContent=false")
        return data.get("Items", [])

    def get_emby_selectablefolders(self) -> list:
        return self._get("{server}/emby/Library/SelectableMediaFolders?")

    def get_emby_devices(self) -> dict:
        data = self._get("{server}/emby/Devices?")
        if isinstance(data, list):
            return {"Items": data, "TotalRecordCount": len(data)}
        return data

    def get_session_user_info(self, user_id: str, device_id: str) -> dict:
        import time as _time
        _time.sleep(1)
        sessions = self._get("{server}/emby/Sessions?DeviceId=" + str(device_id))
        if isinstance(sessions, list):
            return sessions[0] if sessions else {}
        return {}

    def is_item_in_library2(self, view_id: str, item_path: str) -> bool:
        try:
            folders = self.get_emby_selectablefolders()
            for folder in folders:
                if folder.get("Id") == view_id:
                    for sub in folder.get("SubFolders", []):
                        if item_path.startswith(sub.get("Path", "")):
                            return True
        except EmbyConnectionError:
            pass
        return False

    def set_movie(self, session_id: str, item_id: str,
                  item_type: str, item_name: str):
        url = (f"{{server}}/emby/Sessions/{str(session_id)}/Viewing"
               f"?ItemType={str(item_type)}&ItemId={str(item_id)}&ItemName={urllib.parse.quote(str(item_name))}")
        self._post(url, {})

    def get_xnoppo_audio_index(self, user_id: str, item_id: str, index: int) -> int:
        info = self.get_item_info(user_id, item_id)
        audio_count = 0
        for stream in info.get("MediaStreams", []):
            if stream.get("Type") == "Audio":
                audio_count += 1
                if stream.get("Index") == index:
                    return audio_count
        return 1

    def get_xnoppo_subs_index(self, user_id: str, item_id: str, index: int) -> int:
        if index < 0:
            return 0
        info = self.get_item_info(user_id, item_id)
        subs_count = 0
        for stream in info.get("MediaStreams", []):
            if stream.get("Type") == "Subtitle":
                subs_count += 1
                if stream.get("Index") == index:
                    return subs_count
        return 0
