# 📽️ Xnoppo Elite V3
[English Version](./README_EN.md)

![Xnoppo Banner](static/img/home_bg.png)

**Xnoppo Elite V3** es una evolución mayor del proyecto original [Xnoppo v2](https://github.com/Srebollo/xnoppo). Se ha rediseñado desde cero para ofrecer una experiencia visual de lujo y una robustez técnica superior.

---

## 🆚 Comparativa: Xnoppo v2 vs Xnoppo V3 Elite

| Característica | Xnoppo v2 | Xnoppo V3 Elite |
| :--- | :--- | :--- |
| **Interfaz de Usuario** | Básica / Funcional | **Cinematográfica (Elite)** |
| **Temas** | Único (Oscuro) | **Dual (Oscuro / Emby Light Style)** |
| **Control de Logs** | Fijo en consola | **Dinámico / Scroll Asistido / Niveles** |
| **Reproducción ISO** | Manual / A veces falla | **Auto-Healing (Reintento automático)** |
| **Navegación Móvil** | Limitada | **Full Responsive (Sliding Drawer)** |
| **Configuración** | Archivo manual | **Dashboard Web Completo** |

### 🚀 ¿Qué se ha mejorado en la V3?
*   **💎 Estética Denon/Emby**: Un diseño de interfaz inspirado en los equipos de gama alta, con fondos dinámicos y micro-animaciones.
*   **🛠️ Motor de Auto-Curación**: Lógica inteligente que detecta fallos en el arranque de archivos pesados y los soluciona sin intervención del usuario.
*   **📊 Consola Pro**: Un visualizador de registros profesional que permite pausar, filtrar y ajustar la verbosidad en tiempo real.
*   **🌍 Multi-Idioma Nativo**: Selector dinámico de idioma (ES/EN) integrado en la cabecera.

---

---

## 🚀 Entorno de Pruebas Certificado
Esta versión ha sido testeada exhaustivamente en la siguiente configuración, garantizando estabilidad total:
*   **Servidor**: Synology DS423+ (Docker).
*   **Reproductor Origen**: Nvidia Shield TV Pro.
*   **Receptor AV**: Denon AVC-X3800H.
*   **Control de Acceso**: Probado con éxito desde navegadores **Chrome** y dispositivos **móviles** (iOS/Android).

---

## 📋 Requisitos del Sistema

### Software y Versiones
*   **Python**: v3.9 o superior.
*   **Docker**: v20.10+ con **Docker Compose**.
*   **Emby Server**: v4.7+ (se recomienda tener habilitado el acceso remoto/API).
*   **Protocolos de Red**: NFS (v3/v4) o SMB (v2/v3).

---

## 🐋 Guía de Instalación Paso a Paso

1.  **Clonar el Repositorio**:
    ```bash
    git clone https://github.com/ophielsamael/emby-chinoppo-bridge.git
    cd emby-chinoppo-bridge
    ```
2.  **Preparar la Configuración**:
    Crea un archivo `config.json` básico o deja que el sistema lo genere tras el primer inicio.
3.  **Desplegar con Docker**:
    ```bash
    docker-compose up -d --build
    ```
4.  **Acceso Inicial**: Entra en `http://TU_IP:8090`. Se abrirá el asistente de bienvenida para seleccionar idioma y tema.

---

## ⚙️ Guía de Configuración y Ajustes Recomendados

Para un funcionamiento "Elite", utiliza estas configuraciones probadas:

### 📡 Servidor y Reproductor
| Opción | Recomendación | ¿Por qué? |
| :--- | :--- | :--- |
| **Protocolo de Red** | **NFS** | Es significativamente más rápido en el arranque de archivos ISO y carpetas BDMV que SMB. |
| **Oppo IP** | **Estática** | Evita que el dashboard pierda la conexión si el router cambia la IP del reproductor. |
| **Refresh Rate** | **5 Segundos** | El equilibrio perfecto entre fluidez de la interfaz y carga de red baja. |

### 🛠️ Opciones Avanzadas
*   **Debug Level (Nivel 0)**: Mantener en 0 para uso diario. Solo subir a 3 si necesitas investigar por qué una ruta no se monta.
*   **Auto-Healing ISO**: **Activado**. Esta función detecta si un ISO no ha cargado tras 20s y re-envía la orden de reproducción automáticamente.

---

## ⏳ Nota Técnica: El "Delay" de 10 Segundos
Es normal experimentar una espera de unos **10 segundos** desde que pulsas "Reproducir" en Emby hasta que el Oppo/Chinoppo arranca. Esto se debe a:
1.  **Handshake de Red**: La señal viaja desde el cliente Emby al Servidor, luego el Servidor emite un evento vía WebSocket que Xnoppo (en Docker) debe capturar y procesar.
2.  **Montaje de Archivo**: El Oppo debe recibir la orden, solicitar acceso a la carpeta SMB/NFS del servidor y cargar el índice del archivo (especialmente lento en ISOs de 80GB+).
3.  **Docker Overhead**: El aislamiento de red de Docker añade una latencia mínima de milisegundos que, sumada al tiempo de respuesta de la API del Oppo, genera este intervalo de preparación.

---

## ❓ Preguntas Frecuentes (FAQ)

**P: ¿Por qué no arranca la película si uso un servidor que no es Synology?**
*   **R:** Si usas servidores como Unraid o TrueNAS, verifica que el puerto 8090 esté libre y que las rutas de red (Paths) coincidan exactamente con lo que el Oppo ve. Synology usa `/volume1/`, mientras que otros sistemas usan rutas distintas.

**P: El log dice "Connection Refused" al intentar hablar con el Oppo.**
*   **R:** Asegúrate de que el Oppo tenga activada la opción de "Network Control" en sus ajustes de red.

**P: Los archivos ISO se quedan en pantalla negra al inicio.**
*   **R:** Esto suele ser un problema de permisos NFS. Asegúrate de que el NAS permita el acceso a la IP del Oppo con privilegios de lectura y "Map root to admin".

---

## ⚠️ Nota para otros Servidores
Aunque este software ha sido perfeccionado para Synology, puede correr en cualquier entorno Docker. Si encuentras errores de montaje o permisos, revisa la sección de **Rutas de Red** en el dashboard para ajustar los reemplazos de texto (ej: cambiar `/volume1/` por tu ruta real).

---
*Desarrollado con ❤️ para la comunidad de entusiastas de Chinoppo.*
