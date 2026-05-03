# Changelog - Xnoppo Elite V3

Todas las novedades y correcciones del orquestador Xnoppo Elite.

## [3.0.3] - 2026-05-03
### Añadido
- **Sincronización de Repositorio**: Redirección del sistema de actualizaciones al repositorio oficial `ophielsamael`.
- **Branding Elite**: Etiqueta de versión "v3.00 Elite Edition" añadida en la configuración avanzada.
- **Traducciones AV**: Añadida la descripción para la función 'AV Always ON' en el diccionario i18n.

## [3.0.2] - 2026-05-03
### Añadido
- **Localización Total (i18n)**: Soporte completo para Inglés y Español en toda la interfaz (Dashboard, Configuración, Remote).
- **Sistema de Auto-Actualización**: Nuevo widget en la barra lateral para buscar e instalar actualizaciones desde la web.
- **Nuevo Widget de Software**: Reubicación de la gestión de versiones a la barra lateral para acceso global.
- **Changelog**: Creación de este archivo para seguimiento de versiones.

### Corregido
- **Unraid/Synology Fix**: Corregido error `TypeError: can only concatenate str (not "int") to str` al montar rutas de red.
- **Log Visibility**: Reparado fallo de sintaxis que impedía ver los logs en la página de estado.
- **Notificaciones Silenciosas**: Eliminados avisos innecesarios al cargar la página de configuración avanzada.
- **Estabilidad de Montaje**: Optimización en la reconexión NFS/SMB tras fallos de red.

## [3.0.1] - 2026-05-02
### Añadido
- **Auto-Update Engine**: Implementación inicial de la búsqueda de actualizaciones vía GitHub.
- **Drivers AV/TV**: Soporte para marcas adicionales de receptores y automatización de HDMI.

### Corregido
- **Race Conditions**: Mejorada la lógica de hilos para evitar reproducciones duplicadas.

---
*Xnoppo Elite V3 - Powered by Antigravity Engine*
