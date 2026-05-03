# Unraid Installation Guide - Xnoppo Elite V3

This guide provides step-by-step instructions for installing Xnoppo Elite V3 on an Unraid server using **Compose Manager Plus**.

### 1. Share Preparation
1. Go to the **"Shares"** tab in your Unraid interface.
2. Create a new folder (Share), for example named `xnoppo-nextgen`.
3. Unzip the ZIP file downloaded from GitHub into that folder.

### 2. Manager Installation
1. Ensure you have the **"Compose Manager Plus"** plugin installed from the "Apps" tab. This plugin is essential for managing the installation using YAML files directly from the Unraid interface.

### 3. Stack Configuration
1. Go to the **"Docker"** tab in Unraid.
2. Click on **"Add Stack"**.
3. Go to the Stack settings, select the **"Compose"** tab, and paste the following YAML code:

```yaml
version: '3.8'

services:
  xnoppo-nextgen:
    build: /mnt/user/appdata/xnoppo-nextgen
    container_name: xnoppo-nextgen
    ports:
      - "8090:8090"
    volumes:
      - /mnt/user/appdata/xnoppo-nextgen:/app
    restart: always
```

> [!IMPORTANT]
> If you chose a different folder name in step 1, make sure to update the paths `/mnt/user/appdata/xnoppo-nextgen` in the code above.

### 4. WebUI & Icon (Optional)
In the **"WebUI Labels"** tab, you can configure the visual experience:
* Set the interface URL using your Unraid server's IP and port `8090`.
* This will allow the Xnoppo web interface to open directly when you click the container icon on the Unraid dashboard.

### 5. Deployment
1. Click **"Compose Up"** within the Stack to create and run the container.
2. Once the process is finished, access your Unraid IP via port 8090.
3. The Xnoppo Elite V3 welcome and configuration menu will appear.

---
*Xnoppo Elite V3 — Power and Control*
