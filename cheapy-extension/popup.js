// cheapy-extension/popup.js

document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENTOS DE LA UI (Sin cambios) ---
    const resultsContainer = document.getElementById('results-container');
    const statusMessage = document.getElementById('status-message');
    const sortSelect = document.getElementById('sort-select');
    const showAllButton = document.getElementById('show-all-button');
    const recommendationsSection = document.getElementById('recommendations');
    const queryTitle = document.getElementById('query-title');
    const backToRecommendationsButton = document.getElementById('back-to-recommendations-button');

    let allResults = [];

    // --- LÓGICA DE INICIO (Sin cambios) ---
    const initialize = async () => {
        const country = await getUserCountry();
        chrome.storage.local.get(['lastSearchQuery'], (result) => {
            const query = result.lastSearchQuery;
            if (query) {
                queryTitle.textContent = `Resultados para: "${query}"`;
                performSearch(query, country);
            } else {
                statusMessage.textContent = 'Realiza una búsqueda en Google para empezar.';
                queryTitle.textContent = 'Cheapy';
            }
        });
    };
    
    // --- MANEJADORES DE EVENTOS Y FUNCIONES DE LA UI (Sin cambios) ---
    sortSelect.addEventListener('change', () => { displayAllResults(); });
    showAllButton.addEventListener('click', () => { showAllView(); });
    backToRecommendationsButton.addEventListener('click', () => { showRecommendationsView(); });
    const showLoadingState = (message) => {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        recommendationsSection.style.display = 'none';
        resultsContainer.style.display = 'none';
        showAllButton.style.display = 'none';
        sortSelect.style.display = 'none';
        backToRecommendationsButton.style.display = 'none';
    };
    const showRecommendationsView = () => {
        statusMessage.style.display = 'none';
        recommendationsSection.style.display = 'block';
        resultsContainer.style.display = 'none';
        showAllButton.style.display = 'block';
        sortSelect.style.display = 'none';
        backToRecommendationsButton.style.display = 'none';
    };
    const showAllView = () => { /* ...código original... */
        statusMessage.style.display = 'none';
        recommendationsSection.style.display = 'none';
        resultsContainer.style.display = 'block';
        showAllButton.style.display = 'none';
        sortSelect.style.display = 'block';
        backToRecommendationsButton.style.display = 'block';
        displayAllResults();
    };
    const getUserCountry = async () => { /* ...código original... */
        try {
            const cache = await chrome.storage.local.get(['userCountry', 'countryCacheTimestamp']);
            const now = new Date().getTime();
            if (cache.userCountry && cache.countryCacheTimestamp && (now - cache.countryCacheTimestamp < 86400000)) {
                return cache.userCountry;
            }
            const response = await fetch("https://ipapi.co/json/");
            if (!response.ok) return "AR";
            const data = await response.json();
            const country = data.country_code || "AR";
            await chrome.storage.local.set({ userCountry: country, countryCacheTimestamp: now });
            return country;
        } catch (error) {
            console.error("Error geolocalizando desde el frontend:", error);
            return "AR";
        }
    };


    // ===================================================================
    // ===               AQUÍ EMPIEZA LA NUEVA LÓGICA                  ===
    // ===================================================================

    /**
     * PASO 1: Inicia la búsqueda en el backend.
     * Esta función ahora solo envía la tarea y obtiene un ID de vuelta.
     */
    const performSearch = async (query, country) => {
        showLoadingState(`Analizando "${query}"...`);
        allResults = [];
        try {
            const response = await fetch(`http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}&country=${country}`);
            if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);

            const data = await response.json();

            if (data.task_id) {
                // ¡Éxito! Tenemos un ID de tarea. Ahora empezamos a preguntar por los resultados.
                showLoadingState('Procesando tu búsqueda...');
                pollForResults(data.task_id);
            } else {
                throw new Error("No se recibió un ID de tarea del servidor.");
            }
        } catch (error) {
            console.error('Error iniciando la búsqueda:', error);
            statusMessage.textContent = `Error de conexión: ${error.message}.`;
        }
    };

    /**
     * PASO 2: Pregunta (poll) por los resultados usando el ID de la tarea.
     * Esta función se llama a sí misma cada 2 segundos hasta que obtiene un resultado.
     */
    const pollForResults = async (taskId, attempts = 0) => {
        const MAX_ATTEMPTS = 30; // Máximo 30 intentos (30 * 2s = 1 minuto de timeout)

        if (attempts >= MAX_ATTEMPTS) {
            statusMessage.textContent = 'La búsqueda está tardando demasiado. Inténtalo de nuevo.';
            return;
        }

        try {
            const response = await fetch(`http://127.0.0.1:8000/resultados/${taskId}`);
            if (!response.ok) throw new Error(`Error del servidor al obtener resultados: ${response.status}`);

            const data = await response.json();

            if (data.status === 'SUCCESS') {
                // ¡LO LOGRAMOS! Los resultados están listos.
                const results = data.results || [];

                if (results.error) {
                     // El worker terminó pero con un error.
                    statusMessage.textContent = `Error en el scraper: ${results.error}`;
                    return;
                }

                if (results.length > 0) {
                    allResults = results;
                    displayRecommendations();
                } else {
                    statusMessage.textContent = 'No se encontraron resultados para tu búsqueda.';
                }
            } else if (data.status === 'FAILURE') {
                // La tarea falló catastróficamente.
                statusMessage.textContent = 'La tarea de búsqueda falló en el servidor.';
            } else {
                // La tarea todavía está en progreso (PENDING). Esperamos y volvemos a preguntar.
                setTimeout(() => pollForResults(taskId, attempts + 1), 2000); // Espera 2 segundos
            }
        } catch (error) {
            console.error('Error durante el sondeo de resultados:', error);
            statusMessage.textContent = `Error de conexión al obtener resultados: ${error.message}`;
        }
    };


    // --- FUNCIONES DE RENDERIZADO (Sin cambios) ---
    const displayRecommendations = () => { /* ...código original... */
        recommendationsSection.innerHTML = '';
        const cheapest = [...allResults].sort((a, b) => a.price_numeric - b.price_numeric)[0];
        const bestValue = [...allResults].filter(item => item.reviews_count > 0).sort((a, b) => { if (b.rating !== a.rating) return b.rating - a.rating; return b.reviews_count - a.reviews_count; })[0] || cheapest;
        recommendationsSection.appendChild(createResultCard(cheapest, { label: 'Más Barato', className: 'cheapest' }));
        if (cheapest && bestValue && cheapest.url !== bestValue.url) {
            recommendationsSection.appendChild(createResultCard(bestValue, { label: 'Mejor Calidad-Precio', className: 'best-value' }));
        }
        showAllButton.textContent = `Ver los ${allResults.length} resultados`;
        showRecommendationsView();
    };
    const displayAllResults = () => { /* ...código original... */
        resultsContainer.innerHTML = '';
        const sortedResults = [...allResults];
        const sortBy = sortSelect.value;
        if (sortBy === 'price_asc') sortedResults.sort((a, b) => a.price_numeric - b.price_numeric);
        else if (sortBy === 'price_desc') sortedResults.sort((a, b) => b.price_numeric - b.price_numeric);
        else if (sortBy === 'reviews') sortedResults.sort((a, b) => b.reviews_count - a.reviews_count);
        sortedResults.forEach(item => resultsContainer.appendChild(createResultCard(item)));
    };
    const createResultCard = (item, categoryInfo = {}) => { /* ...código original... */
        if (!item) return document.createDocumentFragment();
        const li = document.createElement('li'); li.className = 'result-card';
        const a = document.createElement('a'); a.href = item.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.className = 'result-card-link';
        const img = document.createElement('img'); img.src = item.image_url || 'icons/placeholder.png'; img.alt = item.title; img.className = 'result-image'; img.loading = 'lazy'; a.appendChild(img);
        const textContent = document.createElement('div'); textContent.className = 'result-text-content';
        let categoryHTML = ''; if (categoryInfo.label) { categoryHTML = `<span class="category-badge ${categoryInfo.className}">${categoryInfo.label}</span>`; }
        const formattedPrice = item.price_numeric ? new Intl.NumberFormat('es-AR', { style: 'currency', currency: item.currency || 'ARS' }).format(item.price_numeric) : 'Precio no disponible';
        const reviewsText = item.reviews_count > 0 ? `⭐ ${item.rating || '?'} (${item.reviews_count})` : 'Sin reseñas';
        textContent.innerHTML = `${categoryHTML}<span class="item-title">${item.title || 'Título no disponible'}</span><div class="item-details"><span class="item-price">${formattedPrice}</span><span class="store-name">${item.source || 'Tienda'}</span></div><span class="item-reviews">${reviewsText}</span>`;
        a.appendChild(textContent); li.appendChild(a); return li;
    };


    // --- Iniciar la aplicación ---
    initialize();
});