
const translations = {
    es: {
        home: "Inicio",
        emby_server: "Servidor Emby",
        oppo_player: "Reproductor Oppo",
        libraries: "Bibliotecas",
        paths: "Rutas",
        tv: "Televisor",
        avr: "Receptor AV",
        other: "Otros",
        status: "Estado",
        remote: "Control Remoto",
        help: "Ayuda",
        welcome: "Bienvenido a Xnoppo",
        config_desc: "Configuración inicial — introduce las IPs y las credenciales para comenzar",
        save: "Guardar",
        test_oppo: "Probar Oppo",
        emby_account: "Cuenta Emby",
        user: "Usuario",
        pass: "Contraseña",
        test_emby: "Probar conexión Emby",
        loading: "Cargando...",
        connected: "Conectado",
        not_connected: "Sin conexión",
        sys_status: "Estado del Sistema",
        playback: "Reproducción",
        title: "Título",
        cpu: "CPU",
        memory: "Memoria",
        current_playback: "Reproducción actual",
        log: "Log del sistema",
        refresh_log: "Refrescar Log",
        restart_app: "Reiniciar App",
        theme: "Tema",
        language: "Idioma",
        select_lang: "Seleccionar Idioma",
        dark: "Oscuro",
        light: "Claro",
        deep_blue: "Azul Profundo",
        glass: "Cristal",
        lang_welcome: "Por favor, selecciona tu idioma",
        news_4k: "Novedades 4K",
        news_subtitle: "Próximos lanzamientos",
    },
    en: {
        home: "Home",
        emby_server: "Emby Server",
        oppo_player: "Oppo Player",
        libraries: "Libraries",
        paths: "Paths",
        tv: "TV",
        avr: "AV Receiver",
        other: "Other",
        status: "Status",
        remote: "Remote Control",
        help: "Help",
        welcome: "Welcome to Xnoppo",
        config_desc: "Initial configuration — enter IPs and credentials to start",
        save: "Save",
        test_oppo: "Test Oppo",
        emby_account: "Emby Account",
        user: "User",
        pass: "Password",
        test_emby: "Test Emby Connection",
        loading: "Loading...",
        connected: "Connected",
        not_connected: "Not Connected",
        sys_status: "System Status",
        playback: "Playback",
        title: "Title",
        cpu: "CPU",
        memory: "Memory",
        current_playback: "Current Playback",
        log: "System Log",
        refresh_log: "Refresh Log",
        restart_app: "Restart App",
        theme: "Theme",
        language: "Language",
        select_lang: "Select Language",
        dark: "Dark",
        light: "Light",
        deep_blue: "Deep Blue",
        glass: "Glass",
        lang_welcome: "Please, select your language",
        news_4k: "4K Releases",
        news_subtitle: "Upcoming movies",
    }
};

const i18n = {
    currentLang: localStorage.getItem('xnoppo_lang') || 'es',
    
    init() {
        this.applyTranslations();
    },

    setLanguage(lang) {
        this.currentLang = lang;
        localStorage.setItem('xnoppo_lang', lang);
        this.applyTranslations();
        location.reload();
    },

    t(key) {
        return translations[this.currentLang][key] || key;
    },

    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = this.t(key);
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });
    }
};

window.i18n = i18n;
document.addEventListener('DOMContentLoaded', () => i18n.init());
