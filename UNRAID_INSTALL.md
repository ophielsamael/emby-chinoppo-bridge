# Guía de Instalación en Unraid - Xnoppo Elite V3
# Gracias a la Colaboracion de deibit
Esta guía detalla los pasos para instalar Xnoppo Elite V3 en un servidor Unraid utilizando **Compose Manager Plus**.

### 1. Preparación de la Carpeta (Share)
1. Ve a la pestaña **"Shares"** en tu interfaz de Unraid.
2. Crea una nueva carpeta, por ejemplo con el nombre `xnoppo-nextgen`.
3. Descomprime el archivo ZIP descargado de GitHub dentro de esa carpeta.

### 2. Instalación del Gestor
1. Asegúrate de tener instalado el plugin **"Compose Manager Plus"** desde la pestaña "Apps". Este plugin es esencial para gestionar la instalación mediante archivos YAML desde la interfaz de Unraid.

### 3. Configuración del Stack
1. Ve a la pestaña **"Docker"** de Unraid.
2. Haz clic en **"Add Stack"** (Añadir Stack).
3. Entra en la configuración del Stack, ve a la pestaña **"Compose"**, y pega el siguiente código YAML:

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
> Si has elegido un nombre de carpeta distinto en el paso 1, asegúrate de actualizar las rutas `/mnt/user/appdata/xnoppo-nextgen` en el código anterior.

### 4. Interfaz Web e Icono (Opcional)
En la pestaña **"WebUI Labels"** puedes configurar la experiencia visual:
* Configura la URL de la interfaz usando la IP de tu servidor Unraid y el puerto `8090`.
* Esto permitirá que al hacer clic en el icono del contenedor en el dashboard de Unraid se abra directamente la web de Xnoppo.

### 5. Despliegue
1. Haz clic en **"Compose Up"** dentro del Stack para crear y ejecutar el contenedor.
2. Una vez que el proceso finalice, accede a la IP de tu Unraid por el puerto 8090.
3. Aparecerá el menú de bienvenida y configuración de Xnoppo Elite V3.

---
*Xnoppo Elite V3 — Potencia y Control*
