document.addEventListener('DOMContentLoaded', () => {
    // Referencias a los elementos (SIN CAMBIOS)
    const resultsContainer = document.getElementById('results-container');
    const statusMessage = document.getElementById('status-message');
    const sortSelect = document.getElementById('sort-select');
    const showAllButton = document.getElementById('show-all-button');
    const recommendationsSection = document.getElementById('recommendations');
    const queryTitle = document.getElementById('query-title');
    const backToRecommendationsButton = document.getElementById('back-to-recommendations-button');

    let allResults = [];

    // --- 1. NUEVA FUNCIÓN AÑADIDA ---
    // Esta función se encarga de obtener el país del usuario, usando un caché
    // en la propia extensión para evitar llamadas innecesarias a la API.
    const getUserCountry = async () => {
        try {
            const cache = await chrome.storage.local.get(['userCountry', 'countryCacheTimestamp']);
            const now = new Date().getTime();

            if (cache.userCountry && cache.countryCacheTimestamp && (now - cache.countryCacheTimestamp < 86400000)) { // 24 horas
                console.log("País desde caché de extensión:", cache.userCountry);
                return cache.userCountry;
            }

            console.log("Llamando a API de geolocalización desde la extensión...");
            const response = await fetch("https://ipapi.co/json/");
            if (!response.ok) return "AR"; // Fallback

            const data = await response.json();
            const country = data.country_code || "AR";
            
            await chrome.storage.local.set({ userCountry: country, countryCacheTimestamp: now });
            console.log("País guardado en caché de extensión:", country);
            return country;
        } catch (error) {
            console.error("Error geolocalizando desde el frontend:", error);
            return "AR"; // Fallback en caso de error
        }
    };

    // --- 2. LÓGICA INICIAL MODIFICADA ---
    // Ahora es 'async' para poder usar 'await' y esperar el país.
    const initialize = async () => {
        // Obtenemos el país ANTES de hacer nada más.
        const country = await getUserCountry();
        
        // El resto de la lógica es la misma, pero ya tenemos el país.
        chrome.storage.local.get(['lastSearchQuery'], (result) => {
            const query = result.lastSearchQuery;
            if (query) {
                queryTitle.textContent = `Resultados para: "${query}"`;
                // Pasamos el país obtenido a la función de búsqueda.
                performSearch(query, country);
            } else {
                statusMessage.textContent = 'Realiza una búsqueda en Google para empezar.';
                queryTitle.textContent = 'Cheapy';
            }
        });
    };

    // --- MANEJADORES DE EVENTOS (SIN CAMBIOS) ---
    sortSelect.addEventListener('change', () => { displayAllResults(); });
    showAllButton.addEventListener('click', () => { showAllView(); });
    backToRecommendationsButton.addEventListener('click', () => { showRecommendationsView(); });
    
    // --- FUNCIONES PARA CONTROLAR LA VISIBILIDAD DE LA UI (SIN CAMBIOS) ---
    const showLoadingState = (query) => { /* ...código original... */
        statusMessage.textContent = `Analizando "${query}"...`;
        statusMessage.style.display = 'block';
        recommendationsSection.style.display = 'none';
        resultsContainer.style.display = 'none';
        showAllButton.style.display = 'none';
        sortSelect.style.display = 'none';
        backToRecommendationsButton.style.display = 'none';
    };
    const showRecommendationsView = () => { /* ...código original... */
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

    // --- 3. FUNCIÓN DE BÚSQUEDA MODIFICADA ---
    // Ahora acepta 'country' como segundo argumento.
    const performSearch = async (query, country) => {
        showLoadingState(query);
        allResults = [];
        try {
            // Se añade el parámetro &country=${country} a la URL del fetch.
            const response = await fetch(`http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}&country=${country}`);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                const detail = errorData?.detail || `Error del servidor: ${response.status}`;
                throw new Error(detail);
            }

            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                allResults = data.results;
                displayRecommendations();
            } else {
                statusMessage.textContent = 'No se encontraron resultados.';
            }
        } catch (error) {
            console.error('Error en la búsqueda:', error);
            statusMessage.textContent = `Error de conexión: ${error.message}.`;
        }
    };
    
    // --- FUNCIONES DE RENDERIZADO (SIN CAMBIOS) ---
    const displayRecommendations = () => { /* ...código original... */
        recommendationsSection.innerHTML = '';
        const cheapest = [...allResults].sort((a, b) => a.price_numeric - b.price_numeric)[0];
        const bestValue = [...allResults]
            .filter(item => item.reviews_count > 0)
            .sort((a, b) => {
                if (b.rating !== a.rating) return b.rating - a.rating;
                return b.reviews_count - a.reviews_count;
            })[0] || cheapest;
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
        else if (sortBy === 'price_desc') sortedResults.sort((a, b) => b.price_numeric - a.price_numeric);
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

    // Iniciar la aplicación
    initialize();
});