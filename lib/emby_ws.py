"""
Emby WebSocket Client — Xnoppo
Listens to Emby events and triggers playback on the Oppo.
Fixes the `time` variable shadow bug from the original code.
"""

import json
import logging
import threading
import time as _time

from websocket import WebSocketApp

from .emby_http import EmbyHttpClient, EmbyConnectionError

logger = logging.getLogger(__name__)


class EmbyWebSocketClient:
    """Connects to Emby via WebSocket and reacts to play/playstate/general commands."""

    def __init__(self, config):
        self.config = config
        self.EmbySession: EmbyHttpClient | None = None
        self.emby_state = "Init"
        self.stop_flag = False
        self.MonitoredState = ""
        self._ws: WebSocketApp | None = None
        self._trigger_lock = threading.Lock()
        self._user_hints = {}

    def start(self):
        """Connect to Emby, set capabilities, then run WebSocket loop."""
        try:
            self.EmbySession = EmbyHttpClient(self.config)
            self.EmbySession.set_capabilities()
        except (EmbyConnectionError, Exception) as e:
            logger.error("Could not start Emby session: %s", e)
            return

        server = self.config.get("emby_server", "")
        token = self.EmbySession.user_info.get("AccessToken", "")
        uri = (server
               .replace("http://", "ws://")
               .replace("https://", "wss://"))
        uri += f"/?api_key={token}&deviceId=Xnoppo"

        logger.info("Connecting WebSocket to %s", uri)
        self.emby_state = "Run"

        while not self.stop_flag:
            self._ws = WebSocketApp(
                uri,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self._ws.run_forever(ping_interval=10)
            if self.stop_flag:
                break
            logger.info("WebSocket disconnected, reconnecting in 5s...")
            _time.sleep(5)

        logger.info("WebSocket client stopped")

    def stop(self):
        self.stop_flag = True
        if self._ws:
            self._ws.close()

    # ── WebSocket callbacks ────────────────────────────────────────────────

    def _on_open(self, ws):
        logger.info("WebSocket connected")
        self.emby_state = "Opened"
        ws.send('{"MessageType":"SessionsStart","Data":"0,5000"}')

    def _on_close(self, ws, code, msg):
        logger.info("WebSocket closed: %s %s", code, msg)
        self.emby_state = "Closed"

    def _on_error(self, ws, error):
        logger.error("WebSocket error: %s", error)
        self.emby_state = "Error"

    def _on_message(self, ws, msg):
        # Don't log full message — Sessions payloads are huge and would flood the log
        msg_type_preview = msg[17:50] if len(msg) > 17 else msg
        logger.debug("WS msg type: %s", msg_type_preview)
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from WS: %s", msg[:100])
            return

        msg_type = data.get("MessageType", "")
        payload = data.get("Data", {})

        if msg_type == "Play":
            self._handle_play(payload)
        elif msg_type == "Playstate":
            self._handle_playstate(payload)
        elif msg_type == "GeneralCommand":
            self._handle_general_command(payload)
        elif msg_type == "Sessions":
            self._handle_sessions(payload)
        elif msg_type in ("PlaybackStart", "PlaybackProgress"):
            self._handle_playback_event(payload, msg_type)
        elif msg_type == "UserDataChanged":
            self._handle_userdata_hint(payload)
        else:
            logger.debug("Unhandled WS message type: %s", msg_type)

    def _handle_userdata_hint(self, data):
        """Store the last touched ItemId as a 'hint' for when sessions are empty (ISO issue)."""
        user_id = data.get("UserId")
        user_data_list = data.get("UserDataList", [])
        if user_data_list:
            item_id = user_data_list[0].get("ItemId")
            if item_id:
                # Store hint: User XXX just touched Item YYY
                if not hasattr(self, "_user_hints"): self._user_hints = {}
                self._user_hints[user_id] = {
                    "item_id": item_id,
                    "time": _time.time()
                }
                logger.debug("PISTA: El usuario %s ha interactuado con el item %s", user_id, item_id)

    # ── Command handlers ───────────────────────────────────────────────────

    def _handle_play(self, data: dict):
        command = data.get("PlayCommand")
        if command != "PlayNow":
            return

        # Wait if already loading — fixed: use separate counter, not shadowing `time`
        wait_count = 0
        while self.EmbySession and self.EmbySession.playstate in ("Loading", "Replay") and wait_count < 60:
            _time.sleep(3)
            wait_count += 3

        if self.EmbySession and self.EmbySession.playstate == "Playing":
            logger.info("Already playing — switching content")
            t = threading.Thread(target=self._play_other, args=(data,), daemon=True)
        else:
            t = threading.Thread(target=self._play_to_file, args=(data,), daemon=True)
        t.start()

    def _handle_playstate(self, data: dict):
        from .oppo import OppoClient
        cmd = data.get("Command")
        key_map = {
            "Stop": "STP", "Pause": "PAU", "Unpause": "PLA",
            "NextTrack": "NXT", "PreviousTrack": "PRE",
            "Rewind": "REV", "FastForward": "FWD", "PlayPause": "PAU",
        }
        if cmd == "Seek":
            try:
                client = OppoClient(self.config["Oppo_IP"])
                client.set_play_time(data.get("SeekPositionTicks", 0))
            except Exception as e:
                logger.error("Seek failed: %s", e)
        elif cmd in key_map:
            try:
                client = OppoClient(self.config["Oppo_IP"])
                client.send_remote_key(key_map[cmd])
            except Exception as e:
                logger.error("Playstate key failed: %s", e)

    def _handle_general_command(self, data: dict):
        cmd = data.get("Name")
        args = data.get("Arguments", {})
        if not self.EmbySession:
            return
        try:
            from .oppo import OppoClient
            client = OppoClient(self.config["Oppo_IP"])
            params = self.EmbySession.process_data(self.EmbySession.currentdata)
            if cmd == "SetAudioStreamIndex":
                idx = self.EmbySession.get_xnoppo_audio_index(
                    params["ControllingUserId"], params["item_id"], int(args.get("Index", 1))
                )
                client.set_audio_track(idx)
                self.EmbySession.currentdata["AudioStreamIndex"] = int(args.get("Index", 1))
            elif cmd == "SetSubtitleStreamIndex":
                idx = self.EmbySession.get_xnoppo_subs_index(
                    params["ControllingUserId"], params["item_id"], int(args.get("Index", -1))
                )
                client.set_subtitle_track(idx)
                self.EmbySession.currentdata["SubtitleStreamIndex"] = int(args.get("Index", -1))
        except Exception as e:
            logger.error("General command failed: %s", e)

    def _handle_playback_event(self, data, m_type):
        """Handle direct playback events (much faster than waiting for Sessions update)."""
        self._reload_config()
        monitored = str(self.config.get("MonitoredDevice", "")).strip()
        if not monitored: return

        # Check if this event belongs to our monitored device
        s_id = str(data.get("DeviceId", "")).strip()
        s_name = str(data.get("DeviceName", "")).strip()
        mon_low = monitored.lower()
        
        is_match = (s_id == monitored or (s_name.lower() in mon_low or mon_low in s_name.lower()) if s_name else False)
        if not is_match: return

        now_playing = data.get("Item")
        if not now_playing: return

        item_name = now_playing.get("Name", "")
        if self.MonitoredState == item_name: return
        
        if self.EmbySession and self.EmbySession.playstate in ("Loading", "Replay"):
            return

        logger.info("¡EVENTO %s DETECTADO! %s en %s", m_type.upper(), item_name, s_name)
        
        # ── IMMEDIATE KILL (Aggressive Hijack) ──
        if self.EmbySession and data.get("SessionId"):
            try: self.EmbySession.playback_stop(data.get("SessionId"))
            except: pass
            
        self.MonitoredState = item_name
        
        # Construct data packet
        data_packet = {
            "ItemIds": [now_playing.get("Id")],
            "StartIndex": 0,
            "StartPositionTicks": data.get("PlayState", {}).get("PositionTicks", 0),
            "MediaSourceId": data.get("PlayState", {}).get("MediaSourceId", ""),
            "AudioStreamIndex": data.get("PlayState", {}).get("AudioStreamIndex", 1),
            "SubtitleStreamIndex": data.get("PlayState", {}).get("SubtitleStreamIndex", -1),
            "ControllingUserId": data.get("UserId", ""),
            "SessionID": data.get("SessionId", ""),
            "DeviceName": s_name,
            "Device_Id": monitored
        }
        
        t = threading.Thread(target=self._play_to_file, args=(data_packet,), daemon=True)
        t.start()

    def _handle_sessions(self, data):
        # Always reload config to get the latest monitored device selection
        self._reload_config()
        
        monitored = str(self.config.get("MonitoredDevice", "")).strip()
        if not monitored or not isinstance(data, list):
            return

        mon_low = monitored.lower()

        for session in data:
            s_id = str(session.get("DeviceId", "")).strip()
            s_internal_id = str(session.get("InternalDeviceId", "")).strip()
            s_name = str(session.get("DeviceName", "")).strip()
            s_name_low = s_name.lower()
            
            # Robust matching: check DeviceId, InternalDeviceId, or Fuzzy Name
            is_match = (
                s_id == monitored or 
                s_internal_id == monitored or 
                (s_name_low in mon_low or mon_low in s_name_low) if s_name_low else False
            )

            if is_match:
                now_playing = session.get("NowPlayingItem")
                playstate = session.get("PlayState", {})
                
                # 1. IMMEDIATE HINT CHECK (Crucial for ISO speed)
                if not now_playing and playstate:
                    user_id = session.get("UserId")
                    hint = getattr(self, "_user_hints", {}).get(user_id)
                    if hint and (_time.time() - hint["time"] < 20): # Hint valid for 20s
                        # Debounce the info log
                        last_hint_id = getattr(self, "_last_hint_match_id", "")
                        if last_hint_id != hint["item_id"]:
                            logger.info("¡HINT MATCH INSTANTÁNEO! Identificando ISO vía pista de usuario: %s", hint["item_id"])
                            self._last_hint_match_id = hint["item_id"]
                            
                        now_playing = {"Id": hint["item_id"], "Name": "ISO (Vía Pista)"}
                        # Don't delete hint yet, wait for session update to stabilize

                # 2. PROBE if still no item
                # CRITICAL: Only probe if we have a RECENT user hint (within 30s).
                # Without this guard, every Emby heartbeat triggers a 15s probe = NAS at 99% CPU.
                if not now_playing and playstate:
                    user_id = session.get("UserId")
                    hint = getattr(self, "_user_hints", {}).get(user_id)
                    last_cleanup = getattr(self.EmbySession, "last_cleanup_time", 0) if self.EmbySession else 0
                    hint_is_fresh = hint and (_time.time() - hint["time"] < 30) and (hint["time"] > last_cleanup)
                    
                    # Check probe cooldown: don't start a new probe if one ran recently
                    last_probe_time = getattr(self, "_last_probe_time", 0)
                    probe_on_cooldown = (_time.time() - last_probe_time) < 20
                    
                    if hint_is_fresh:
                        # Instant hint match
                        now_playing = {"Id": hint["item_id"], "Name": "ISO (Vía Pista)"}
                    elif not probe_on_cooldown:
                        # Only probe if hint might arrive soon (no cooldown)
                        # Check if session shows playlist activity (not just an idle heartbeat)
                        playlist_len = session.get("PlaylistLength", 0)
                        if playlist_len > 0 or session.get("PlayState", {}).get("CanSeek"):
                            self._last_probe_time = _time.time()
                            logger.debug("RADAR: Actividad real en %s sin Item. Sonda 15s...", s_name)
                            for attempt in range(10):
                                if attempt > 0: _time.sleep(1.5)
                                hint = getattr(self, "_user_hints", {}).get(user_id)
                                if hint and (_time.time() - hint["time"] < 30) and (hint["time"] > last_cleanup):
                                    logger.info("¡HINT CAZADO POR SONDA! Identificando ISO: %s", hint["item_id"])
                                    now_playing = {"Id": hint["item_id"], "Name": "ISO (Vía Pista)"}
                                    break
                                try:
                                    s_full_id = session.get("Id")
                                    s_detail = self.EmbySession.get_session_details(s_full_id)
                                    now_playing = s_detail.get("NowPlayingItem")
                                    if now_playing:
                                        logger.info("Sonda Individual EXITOSA: %s", now_playing.get("Name"))
                                        break
                                except Exception: pass
                            if not now_playing:
                                logger.debug("No se pudo identificar el contenido de %s.", s_name)

                if now_playing:
                    item_name = now_playing.get("Name", "")
                    item_id = now_playing.get("Id")
                    
                    # Global Post-Cleanup Cooldown: Prevent ANY ghost starts for 30s after Xnoppo stops a movie
                    if self.EmbySession:
                        last_cleanup = getattr(self.EmbySession, "last_cleanup_time", 0)
                        if _time.time() - last_cleanup < 30:
                            return
                    
                    # Strict Debounce: Never re-trigger the EXACT same item if Xnoppo is already handling it
                    last_trigger = getattr(self, "_last_trigger", {})
                    last_id = last_trigger.get(s_id)
                    
                    if str(last_id) == str(item_id):
                        if self.EmbySession and self.EmbySession.playstate in ("Loading", "Playing", "Replay"):
                            # It's already playing on the Oppo! Do not restart the movie.
                            return
                        
                        # If playstate is Free, wait at least 30s to avoid double-clicks or ISO re-triggers
                        last_time = last_trigger.get(f"{s_id}_time", 0)
                        if _time.time() - last_time < 30:
                            return

                    # Use lock to prevent simultaneous triggers
                    if not self._trigger_lock.acquire(blocking=False):
                        return
                    
                    try:
                        image_tag = now_playing.get("ImageTags", {}).get("Primary", "")
                        logger.info("¡MATCH! El dispositivo monitorizado (%s) está reproduciendo: %s", s_name, item_name)
                        
                        # ── IMMEDIATE KILL (Aggressive Hijack) ──
                        if self.EmbySession and session.get("Id"):
                            try: self.EmbySession.playback_stop(session.get("Id"))
                            except: pass
                        
                        # ── INSTANT TAKEOVER ──
                        # Assign ID now so old session dies immediately
                        from .playback import get_next_id
                        my_id = get_next_id()
                        
                        # Store info in session
                        if self.EmbySession:
                            self.EmbySession.played_item_id = item_id
                            self.EmbySession.played_image_tag = image_tag

                        if not hasattr(self, "_last_trigger"): self._last_trigger = {}
                        self._last_trigger[s_id] = item_id
                        self._last_trigger[f"{s_id}_time"] = _time.time()
                        
                        self.MonitoredState = item_name
                        logger.info("Iniciando orquestación #%d para: %s", my_id, self.MonitoredState)

                        # Construct data packet for playback
                        data_packet = {
                            "ItemIds": [item_id],
                            "StartIndex": 0,
                            "StartPositionTicks": playstate.get("PositionTicks", 0),
                            "MediaSourceId": playstate.get("MediaSourceId", ""),
                            "AudioStreamIndex": playstate.get("AudioStreamIndex", 1),
                            "SubtitleStreamIndex": playstate.get("SubtitleStreamIndex", -1),
                            "ControllingUserId": session.get("UserId", ""),
                            "SessionID": session.get("Id", ""),
                            "DeviceName": s_name,
                            "Device_Id": monitored,
                            "Session_Internal_Id": my_id # Pass the ID to the thread
                        }
                        
                        # Start orchestration thread IMMEDIATELY
                        if self.EmbySession and self.EmbySession.playstate == "Playing":
                            logger.info("Already playing — switching content")
                            t = threading.Thread(target=self._play_other, args=(data_packet,), daemon=True)
                        else:
                            t = threading.Thread(target=self._play_to_file, args=(data_packet,), daemon=True)
                        t.start()
                    finally:
                        # Hold lock for 2s to absorb duplicate WS events from same Play action
                        _time.sleep(2.0)
                        self._trigger_lock.release()
                    
                elif not now_playing and self.MonitoredState:
                    # Monitor device stopped. Check if we should cleanup or if we are just switching/loading
                    is_busy = self.EmbySession and self.EmbySession.playstate in ("Loading", "Replay")
                    
                    if is_busy:
                        logger.debug("Shield se detuvo, pero Xnoppo está ocupado (%s). Ignorando cleanup.", self.EmbySession.playstate)
                        self.MonitoredState = ""
                        return

                    logger.info("El dispositivo monitorizado ha dejado de reproducir: %s", self.MonitoredState)
                    self.MonitoredState = ""
                    
                    # (Smart Re-trigger handles the cooldown reset now)
                    
                    # Restore AV Input if we have a saved one
                    if self.config.get("AV"):
                        try:
                            from .av_control import av_set_input, av_power_off
                            original_input = self.config.get("_original_av_input")
                            if original_input:
                                logger.info("Restaurando entrada AV tras stop...")
                                av_set_input(self.config, original_input)
                                self.config["_original_av_input"] = None
                            elif not self.config.get("AV_Always_ON"):
                                logger.info("Apagando AV tras stop...")
                                av_power_off(self.config)
                        except Exception as e:
                            logger.error("Error al restaurar AV: %s", e)

    def _play_to_file(self, data: dict):
        """Full playback orchestration — moved from 300-line monolithic function."""
        from .playback import play_to_file
        play_to_file(self.EmbySession, data, self.config)
        # Reload config after playback (settings may have changed)
        self._reload_config()

    def _play_other(self, data: dict):
        from .playback import play_other
        play_other(self.EmbySession, data, self.config)
        self._reload_config()

    def _reload_config(self):
        import json
        try:
            with open(self.EmbySession.config.get("_config_file", "config.json")) as f:
                self.config = json.load(f)
            if self.EmbySession:
                self.EmbySession.config = self.config
        except Exception as e:
            logger.warning("Config reload failed: %s", e)
