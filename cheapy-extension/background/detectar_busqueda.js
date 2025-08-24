// Este archivo inicializa la funcionalidad para detectar la búsqueda del usuario.

export function initializeDetectarBusqueda() {
    // Función para obtener la consulta de una URL de Google y guardarla
    const updateSearchQuery = (url) => {
        try {
            const urlObject = new URL(url);
            if (urlObject.hostname.includes('google.com') && urlObject.pathname === '/search') {
                const query = urlObject.searchParams.get('q');
                if (query) {
                    chrome.storage.local.set({ lastSearchQuery: query });
                }
            }
        } catch (e) {
            // Ignorar URLs inválidas como chrome://newtab
        }
    };

    // 1. Se activa cuando se actualiza la URL dentro de una pestaña (ej: nueva búsqueda)
    chrome.webNavigation.onHistoryStateUpdated.addListener(details => {
        updateSearchQuery(details.url);
    }, { url: [{ hostContains: 'google.com' }] });

    // 2. Se activa cuando el usuario cambia a otra pestaña
    chrome.tabs.onActivated.addListener(activeInfo => {
        chrome.tabs.get(activeInfo.tabId, (tab) => {
            if (tab && tab.url) {
                updateSearchQuery(tab.url);
            }
        });
    });

    // 3. Se activa cuando una pestaña existente se actualiza
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
        if (changeInfo.status === 'complete' && tab.url) {
            updateSearchQuery(tab.url);
        }
    });
}
