/**
 * Módulo de Detección de Búsquedas para la Extensión Chrome Cheapy
 *
 * Monitorea el comportamiento de navegación del usuario para detectar consultas de búsqueda en Google.
 * Captura términos de búsqueda desde URLs de búsqueda de Google y los almacena localmente
 * para uso en la funcionalidad de comparación de precios de la extensión.
 */

/**
 * Inicializa la funcionalidad de detección de búsquedas.
 * Configura múltiples event listeners para capturar consultas de búsqueda desde varias
 * interacciones del usuario con páginas de búsqueda de Google.
 */
export function initializeDetectarBusqueda() {
    /**
     * Extrae y almacena la consulta de búsqueda desde URLs de búsqueda de Google.
     * Parsea el parámetro 'q' desde URLs de búsqueda de Google y lo guarda en almacenamiento local.
     * @param {string} url - La URL a analizar para consultas de búsqueda
     */
    const updateSearchQuery = (url) => {
        try {
            const urlObject = new URL(url);

            // Solo procesar URLs de búsqueda de Google
            if (urlObject.hostname.includes('google.com') && urlObject.pathname === '/search') {
                const query = urlObject.searchParams.get('q');
                if (query) {
                    // Almacenar la consulta de búsqueda para uso posterior del popup
                    chrome.storage.local.set({ lastSearchQuery: query });
                }
            }
        } catch (e) {
            // Ignorar URLs inválidas (ej. chrome://newtab, páginas internas)
        }
    };

    // Event listener: Se activa cuando la URL cambia dentro de una pestaña (ej. nueva búsqueda)
    chrome.webNavigation.onHistoryStateUpdated.addListener(details => {
        updateSearchQuery(details.url);
    }, { url: [{ hostContains: 'google.com' }] });

    // Event listener: Se activa cuando el usuario cambia a otra pestaña
    chrome.tabs.onActivated.addListener(activeInfo => {
        chrome.tabs.get(activeInfo.tabId, (tab) => {
            if (tab && tab.url) {
                updateSearchQuery(tab.url);
            }
        });
    });

    // Event listener: Triggered when an existing tab is updated
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
        // Only process when page loading is complete and URL is available
        if (changeInfo.status === 'complete' && tab.url) {
            updateSearchQuery(tab.url);
        }
    });
}
