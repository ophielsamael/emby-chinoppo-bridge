# 📽️ Xnoppo Elite V3

![Xnoppo Banner](static/img/home_bg.png)

**Xnoppo Elite V3** is a major evolution of the original [Xnoppo v2](https://github.com/Srebollo/xnoppo) project. It has been redesigned from the ground up to offer a luxury visual experience and superior technical robustness.

---

## 🆚 Comparison: Xnoppo v2 vs Xnoppo V3 Elite

| Feature | Xnoppo v2 | Xnoppo V3 Elite |
| :--- | :--- | :--- |
| **User Interface** | Basic / Functional | **Cinematic (Elite)** |
| **Themes** | Single (Dark) | **Dual (Dark / Emby Light Style)** |
| **Log Control** | Fixed in console | **Dynamic / Assisted Scroll / Levels** |
| **ISO Playback** | Manual / Fails sometimes | **Auto-Healing (Auto-retry)** |
| **Mobile Navigation** | Limited | **Full Responsive (Sliding Drawer)** |
| **Configuration** | Manual file | **Full Web Dashboard** |

### 🚀 What's New in V3?
*   **💎 Denon/Emby Aesthetics**: A UI design inspired by high-end hardware, featuring dynamic backgrounds and micro-animations.
*   **🛠️ Auto-Healing Engine**: Intelligent logic that detects failed starts for heavy files and fixes them without user intervention.
*   **📊 Pro Console**: A professional log viewer that allows pausing, filtering, and adjusting verbosity in real-time.
*   **🌍 Native Multi-Language**: Dynamic language selector (ES/EN) integrated into the header.

---

## 🚀 Certified Test Environment
This version has been extensively tested in the following configuration, guaranteeing total stability:
*   **Server**: Synology DS423+ (Docker).
*   **Source Player**: Nvidia Shield TV Pro.
*   **AV Receiver**: Denon AVC-X3800H.
*   **Access Control**: Successfully tested from **Chrome** browsers and **mobile** devices (iOS/Android).

---

## 📋 System Requirements

### Software and Versions
*   **Python**: v3.9 or higher.
*   **Docker**: v20.10+ with **Docker Compose**.
*   **Emby Server**: v4.7+ (API access/remote access recommended).
*   **Network Protocols**: NFS (v3/v4) or SMB (v2/v3).

---

## 🐋 Step-by-Step Installation Guide

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/ophielsamael/emby-chinoppo-bridge.git
    cd emby-chinoppo-bridge
    ```
2.  **Prepare Configuration**:
    Create a basic `config.json` file or let the system generate it after the first run.
3.  **Deploy with Docker**:
    ```bash
    docker-compose up -d --build
    ```
4.  **Initial Access**: Enter `http://YOUR_IP:8090`. The welcome wizard will open to select language and theme.

---

## ⚙️ Configuration Guide & Recommended Settings

For an "Elite" performance, use these proven settings:

### 📡 Server and Player
| Option | Recommendation | Why? |
| :--- | :--- | :--- |
| **Network Protocol** | **NFS** | It is significantly faster at starting ISO files and BDMV folders than SMB. |
| **Oppo IP** | **Static** | Prevents the dashboard from losing connection if the router changes the player's IP. |
| **Refresh Rate** | **5 Seconds** | The perfect balance between UI fluidity and low network load. |

### 🛠️ Advanced Options
*   **Debug Level (Level 0)**: Keep at 0 for daily use. Only increase to 3 if you need to investigate why a path is not mounting.
*   **Auto-Healing ISO**: **Enabled**. This function detects if an ISO hasn't loaded after 20s and re-sends the playback command automatically.

---

## ⏳ Technical Note: The 10-Second Delay
It is normal to experience a wait of about **10 seconds** from when you press "Play" in Emby until the Oppo/Chinoppo starts. This is due to:
1.  **Network Handshake**: The signal travels from the Emby client to the Server, then the Server emits a WebSocket event that Xnoppo (in Docker) must capture and process.
2.  **File Mounting**: The Oppo must receive the command, request access to the server's SMB/NFS folder, and load the file index (especially slow on 80GB+ ISOs).
3.  **Docker Overhead**: Docker's network isolation adds minimal millisecond latency which, added to the Oppo's API response time, creates this preparation interval.

---

## ❓ Frequently Asked Questions (FAQ)

**Q: Why doesn't the movie start if I use a server other than Synology?**
*   **A:** If you use servers like Unraid or TrueNAS, check that port 8090 is free and that network paths exactly match what the Oppo sees. Synology uses `/volume1/`, while other systems use different paths.

**Q: The log says "Connection Refused" when trying to talk to the Oppo.**
*   **A:** Ensure the Oppo has "Network Control" enabled in its network settings.

**Q: ISO files stay on a black screen at startup.**
*   **A:** This is usually an NFS permission issue. Ensure the NAS allows access to the Oppo's IP with read privileges and "Map root to admin".

---

## ⚠️ Note for other Servers
Although this software has been perfected for Synology, it can run in any Docker environment. If you encounter mount or permission errors, check the **Network Paths** section in the dashboard to adjust text replacements (e.g., change `/volume1/` to your real path).

---
*Developed with ❤️ for the Chinoppo enthusiast community.*
