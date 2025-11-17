document.addEventListener('DOMContentLoaded', () => {
    // --- REFERENCIAS A ELEMENTOS DEL DOM ---
    const statusMessage = document.getElementById('status-message');
    const queryTitle = document.getElementById('query-title');
    const recommendationsView = document.getElementById('recommendations-view');
    const allResultsView = document.getElementById('all-results-view');
    const recommendationsSection = document.getElementById('recommendations');
    const showAllButton = document.getElementById('show-all-button');
    const sortSelect = document.getElementById('sort-select');
    const resultsContainer = document.getElementById('results-container');
    const backToRecommendationsButton = document.getElementById('back-to-recommendations-button');
    const similarityCheckbox = document.getElementById('similarity-checkbox');

    let allResults = [];

    // --- FUNCIÓN CENTRAL PARA CONTROLAR LA VISTA ---
    const switchView = (viewName) => {
        // Ocultamos todos los contenedores principales para empezar de cero
        statusMessage.style.display = 'none';
        recommendationsView.style.display = 'none';
        allResultsView.style.display = 'none';

        // Mostramos solo el contenedor que corresponde a la vista actual
        switch (viewName) {
            case 'loading':
                statusMessage.style.display = 'block';
                break;
            case 'recommendations':
                recommendationsView.style.display = 'flex';
                break;
            case 'all':
                allResultsView.style.display = 'flex';
                break;
            default: // Por si acaso, mostramos el estado de carga
                statusMessage.style.display = 'block';
                break;
        }
    };
    // --- NUEVA FUNCIÓN DE GEOLOCALIZACIÓN CON CACHÉ EN LA EXTENSIÓN ---
    const getUserCountry = async () => {
        try {
            const cache = await chrome.storage.local.get(['userCountry', 'countryCacheTimestamp']);
            const now = new Date().getTime();

            // Usar caché si es válido (menos de 24 horas)
            if (cache.userCountry && cache.countryCacheTimestamp && (now - cache.countryCacheTimestamp < 86400000)) {
                console.log("País desde caché de extensión:", cache.userCountry);
                return cache.userCountry;
            }

            // Si no hay caché, llamar a la API. Esta API (ip-api.com) es más permisiva con CORS.
            console.log("Llamando a API de geolocalización desde la extensión...");
            const response = await fetch("http://ip-api.com/json/?fields=countryCode");
            if (!response.ok) return "AR"; // Fallback

            const data = await response.json();
            const country = data.countryCode || "AR";
            
            await chrome.storage.local.set({ userCountry: country, countryCacheTimestamp: now });
            console.log("País guardado en caché de extensión:", country);
            return country;
        } catch (error) {
            console.error("Error geolocalizando desde el frontend:", error);
            return "AR"; // Fallback en caso de error
        }
    };

    // --- LÓGICA DE INICIO MODIFICADA ---
    const initialize = async () => {
        // Obtenemos el país ANTES de hacer la búsqueda
        const country = await getUserCountry();
        
        chrome.storage.local.get(['lastSearchQuery'], (result) => {
            const query = result.lastSearchQuery;
            if (query) {
                queryTitle.textContent = `Resultados para: "${query}"`;
                // Pasamos el país a la función de búsqueda
                performSearch(query, country);
            } else {
                queryTitle.textContent = 'Cheapy';
                statusMessage.textContent = 'Realiza una búsqueda en Google para empezar.';
                switchView('loading');
            }
        });
    };


    // --- LÓGICA DE BÚSQUEDA Y POLLING ---
    const performSearch = async (query, country) => {
        statusMessage.textContent = `Analizando "${query}"...`;
        switchView('loading');
        
        try {
            // ¡AÑADIMOS DE NUEVO EL PARÁMETRO &country!
            const searchResponse = await fetch(`http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}&country=${country}`);
            if (!searchResponse.ok) throw new Error("Error al iniciar la búsqueda.");
            // ... (el resto de la función es idéntico a tu versión actual)
            const taskData = await searchResponse.json();
            if (taskData.error) { /* ... */ }
            if (taskData.task_id) { pollForResult(taskData.task_id); } 
            else { throw new Error("No se recibió un ID de tarea."); }
        } catch (error) {
            statusMessage.textContent = `Error de conexión: ${error.message}`;
        }
    };
    
    const pollForResult = async (taskId, attempt = 1) => {
        const maxAttempts = 45;
        if (attempt > maxAttempts) {
            statusMessage.textContent = "La búsqueda tardó demasiado.";
            return;
        }
        try {
            const resultResponse = await fetch(`http://127.0.0.1:8000/resultados/${taskId}`);
            if (!resultResponse.ok) throw new Error("Error al obtener resultados.");
            const resultData = await resultResponse.json();

            if (resultData.status === 'SUCCESS') {
                allResults = resultData.results || [];
                if (allResults.length > 0) {
                    displayRecommendations();
                } else {
                    statusMessage.textContent = 'No se encontraron resultados.';
                    switchView('loading');
                }
            } else if (resultData.status === 'FAILURE') {
                statusMessage.textContent = "Ocurrió un error en el servidor.";
                switchView('loading');
            } else { // PENDING
                statusMessage.textContent = `Procesando... (${resultData.completed || '0/?'})`;
                setTimeout(() => pollForResult(taskId, attempt + 1), 2000);
            }
        } catch (error) {
            statusMessage.textContent = `Error al verificar resultados: ${error.message}`;
            switchView('loading');
        }
    };

    // --- MANEJADORES DE EVENTOS ---
    sortSelect.addEventListener('change', () => displayAllResults());
    similarityCheckbox.addEventListener('change', () => displayAllResults());
    
    showAllButton.addEventListener('click', () => {
        switchView('all');
        displayAllResults();
    });
    
    backToRecommendationsButton.addEventListener('click', () => {
        switchView('recommendations');
    });

    // --- FUNCIONES DE RENDERIZADO ---
    const displayRecommendations = () => {
        recommendationsSection.innerHTML = '';
        const cheapest = [...allResults].sort((a, b) => {
            const simA = a.similarity_score || 0;
            const simB = b.similarity_score || 0;
            if (simB !== simA) return simB - simA;
            return a.price_numeric - b.price_numeric;
        })[0];
        const bestValue = [...allResults].filter(item => item.reviews_count > 0).sort((a, b) => {
            const simA = a.similarity_score || 0;
            const simB = b.similarity_score || 0;
            if (simB !== simA) return simB - simA;
            if (b.rating - a.rating !== 0) return b.rating - a.rating;
            return b.reviews_count - a.reviews_count;
        })[0] || cheapest;
        
        if (cheapest) recommendationsSection.appendChild(createResultCard(cheapest, { label: 'Más Barato', className: 'cheapest' }));
        if (bestValue && (!cheapest || cheapest.url !== bestValue.url)) {
            recommendationsSection.appendChild(createResultCard(bestValue, { label: 'Mejor Calidad-Precio', className: 'best-value' }));
        }
        
        showAllButton.textContent = `Ver los ${allResults.length} resultados`;
        switchView('recommendations'); // Cambiamos a la vista de recomendaciones
    };

    const displayAllResults = () => {
        resultsContainer.innerHTML = '';
        const sortedResults = [...allResults];
        const sortBy = sortSelect.value;
        const similarityChecked = similarityCheckbox.checked;
        sortedResults.sort((a, b) => {
            if (similarityChecked) {
                const simA = a.similarity_score || 0;
                const simB = b.similarity_score || 0;
                if (simB !== simA) return simB - simA;
            }
            const priceA = a.price_numeric ?? Infinity; const priceB = b.price_numeric ?? Infinity;
            const reviewsA = a.reviews_count ?? 0; const reviewsB = b.reviews_count ?? 0;
            const ratingA = a.rating ?? 0; const ratingB = b.rating ?? 0;
            const discA = (typeof a.discount_percent === 'number') ? a.discount_percent : (a.price_before_numeric && a.price_numeric ? Math.max(0, ((a.price_before_numeric - a.price_numeric) / a.price_before_numeric) * 100) : 0);
            const discB = (typeof b.discount_percent === 'number') ? b.discount_percent : (b.price_before_numeric && b.price_numeric ? Math.max(0, ((b.price_before_numeric - b.price_numeric) / b.price_before_numeric) * 100) : 0);
            switch (sortBy) {
                case 'price_asc': return priceA - priceB;
                case 'price_desc': return priceB - priceA;
                case 'reviews': return reviewsB - reviewsA;
                case 'deal_desc':
                    // Ordenar primero los que están en oferta y luego por mayor porcentaje de descuento
                    if ((b.on_sale === true) !== (a.on_sale === true)) {
                        return (b.on_sale === true) ? 1 : -1;
                    }
                    return (discB || 0) - (discA || 0);
                case 'relevance': default:
                    if (ratingB !== ratingA) { return ratingB - ratingA; }
                    return reviewsB - reviewsA;
            }
        });
        sortedResults.forEach(item => resultsContainer.appendChild(createResultCard(item)));
    };

    const createResultCard = (item, categoryInfo = {}) => {
        if (!item) return document.createDocumentFragment();
        const li = document.createElement('li'); li.className = 'result-card';
        const a = document.createElement('a');
        a.href = item.url;
        a.rel = 'noopener noreferrer';
        a.className = 'result-card-link';
        a.target = '_blank';
        a.addEventListener('click', (event) => {
            event.preventDefault(); // Detiene el comportamiento de enlace HTML
            
            // Usamos chrome.tabs.create para abrir la URL
            chrome.tabs.create({
                url: item.url,
                active: false // <--- ESTO ES LA CLAVE: No se activa la nueva pestaña
            });
        });
        const img = document.createElement('img'); img.src = item.image_url || 'icons/placeholder.png'; img.alt = item.title; img.className = 'result-image'; img.loading = 'lazy'; a.appendChild(img);
        const textContent = document.createElement('div'); textContent.className = 'result-text-content';
        let categoryHTML = ''; if (categoryInfo.label) { categoryHTML = `<span class="category-badge ${categoryInfo.className}">${categoryInfo.label}</span>`; }
        
        // Formatear precio numérico y obtener precio crudo si está disponible
        const formattedPriceNumeric = item.price_numeric ? new Intl.NumberFormat(undefined, { style: 'currency', currency: item.currency || 'USD' }).format(item.price_numeric) : null;
    // Prefer the cleaned/display price from backend if available
    const rawPrice = item.price_display ? String(item.price_display).trim() : (item.price ? String(item.price).trim() : null);

        // Construir HTML para precio. Si está en oferta y el spider nos dio el precio crudo, usamos ese texto
        let priceHTML = '';
        if (item.on_sale && rawPrice) {
            const discountPercent = item.discount_percent ? Math.round(item.discount_percent) : null;
            priceHTML = `<span class="item-price on-sale">${rawPrice}</span>`;
            if (discountPercent !== null) {
                priceHTML += `<span class="discount-badge">-${discountPercent}%</span>`;
            }
        } else if (formattedPriceNumeric) {
            priceHTML = `<span class="item-price">${formattedPriceNumeric}</span>`;
        } else {
            priceHTML = `<span class="item-price">Precio no disponible</span>`;
        }
        
        const reviewsText = item.reviews_count > 0 ? `⭐ ${item.rating || '?'} (${item.reviews_count})` : 'Sin reseñas';
    textContent.innerHTML = `${categoryHTML}<span class="item-title">${item.title || 'Título no disponible'}</span><div class="item-details">${priceHTML}<span class="store-name">${item.source || 'Tienda'}</span></div><span class="item-reviews">${reviewsText}</span>`;
        a.appendChild(textContent); li.appendChild(a); return li;
    };

    // --- Iniciar la aplicación ---
    initialize();
});