# Changelog - Xnoppo Elite V3

## [3.0.4] - 2026-05-03
### 🇪🇸 Español
#### Corregido
- **Blindaje de Tipos (Emby)**: Corregido error crítico `TypeError` al concatenar IDs de Emby en servidores donde se interpretan como números.
- **Estabilidad de API**: Refactorización de la comunicación HTTP para prevenir fallos de concatenación de cadenas.

### 🇬🇧 English
#### Fixed
- **Type Safety (Emby)**: Fixed critical `TypeError` when concatenating Emby IDs on servers where they are interpreted as integers.
- **API Stability**: Refactored HTTP communication to prevent string concatenation crashes.

---

## [3.0.3] - 2026-05-03
### 🇪🇸 Español
#### Añadido
- **Sincronización de Repositorio**: Redirección del sistema de actualizaciones al repositorio oficial `ophielsamael`.
- **Branding Elite**: Etiqueta de versión "v3.00 Elite Edition" añadida en la configuración avanzada.
- **Traducciones**: Añadida la descripción para la función en el diccionario i18n.

### 🇬🇧 English
#### Added
- **Repository Sync**: Redirected the update system to the official `ophielsamael` repository.
- **Elite Branding**: Added "v3.00 Elite Edition" version tag in advanced settings.
- **AV Translations**: Added the description for 'AV Always ON' in the i18n dictionary.

---

## [3.0.2] - 2026-05-03
### 🇪🇸 Español
#### Añadido
- **Localización Total (i18n)**: Soporte completo para Inglés y Español en toda la interfaz.
- **Sistema de Auto-Actualización**: Nuevo widget en la barra lateral para buscar actualizaciones.
- **Nuevo Widget de Software**: Reubicación de la gestión de versiones a la barra lateral.

#### Corregido
- **Unraid/Synology Fix**: Corregido error de concatenación al montar rutas de red.
- **Log Visibility**: Reparado fallo que impedía ver los logs en la página de estado.

### 🇬🇧 English
#### Added
- **Full Localization (i18n)**: Full support for English and Spanish across the entire interface.
- **Auto-Update System**: New sidebar widget to check for updates globally.
- **New Software Widget**: Relocated version management to the sidebar for better accessibility.

#### Fixed
- **Unraid/Synology Fix**: Fixed string/int concatenation error when mounting network paths.
- **Log Visibility**: Fixed syntax error that prevented logs from showing on the status page.

---
*Xnoppo Elite V3*
