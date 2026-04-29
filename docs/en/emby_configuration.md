# Emby configuration quick guide

> This repository does **not** include an Emby web interface.
> Use your Emby Server dashboard for these settings.

## 1) Configure Emby access (local / remote)

1. Open your Emby dashboard (`http://<server-ip>:8096`).
2. Go to **Settings** (gear icon).
3. Open **Network**.
4. Review:
   - **Local HTTP port** (default `8096`)
   - **HTTPS port** (if enabled)
   - **Allow remote connections to this Emby Server**
5. Save and restart Emby if requested.

## 2) Configure movie folders (media libraries)

1. In Emby dashboard, go to **Settings** → **Library**.
2. Choose **Add Media Library** (or edit an existing one).
3. Select **Movies** as content type.
4. In **Folders**, add paths (e.g. `/volume1/media/movies`).
5. Save and run a library scan.

## 3) Recommended permissions check

```bash
namei -l /volume1/media/movies

