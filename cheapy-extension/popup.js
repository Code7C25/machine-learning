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

    // --- LÓGICA DE INICIO ---
    const initialize = () => {
        chrome.storage.local.get(['lastSearchQuery'], (result) => {
            const query = result.lastSearchQuery;
            if (query) {
                queryTitle.textContent = `Resultados para: "${query}"`;
                performSearch(query);
            } else {
                queryTitle.textContent = 'Cheapy';
                statusMessage.textContent = 'Realiza una búsqueda en Google para empezar.';
                switchView('loading');
            }
        });
    };

    // --- LÓGICA DE BÚSQUEDA Y POLLING ---
    const performSearch = async (query) => {
        statusMessage.textContent = `Analizando "${query}"...`;
        switchView('loading');
        
        try {
            const searchResponse = await fetch(`http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}`);
            if (!searchResponse.ok) throw new Error("Error al iniciar la búsqueda.");
            const taskData = await searchResponse.json();
            
            if (taskData.error) {
                 statusMessage.textContent = taskData.error;
                 return;
            }
            if (taskData.task_id) {
                pollForResult(taskData.task_id);
            } else { throw new Error("No se recibió un ID de tarea."); }
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
        const cheapest = [...allResults].sort((a, b) => a.price_numeric - b.price_numeric)[0];
        const bestValue = [...allResults].filter(item => item.reviews_count > 0).sort((a, b) => (b.rating - a.rating) || (b.reviews_count - a.reviews_count))[0] || cheapest;
        
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
        sortedResults.sort((a, b) => {
            const priceA = a.price_numeric ?? Infinity; const priceB = b.price_numeric ?? Infinity;
            const reviewsA = a.reviews_count ?? 0; const reviewsB = b.reviews_count ?? 0;
            const ratingA = a.rating ?? 0; const ratingB = b.rating ?? 0;
            switch (sortBy) {
                case 'price_asc': return priceA - priceB;
                case 'price_desc': return priceB - priceA;
                case 'reviews': return reviewsB - reviewsA;
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
        const a = document.createElement('a'); a.href = item.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.className = 'result-card-link';
        const img = document.createElement('img'); img.src = item.image_url || 'icons/placeholder.png'; img.alt = item.title; img.className = 'result-image'; img.loading = 'lazy'; a.appendChild(img);
        const textContent = document.createElement('div'); textContent.className = 'result-text-content';
        let categoryHTML = ''; if (categoryInfo.label) { categoryHTML = `<span class="category-badge ${categoryInfo.className}">${categoryInfo.label}</span>`; }
        const formattedPrice = item.price_numeric ? new Intl.NumberFormat(undefined, { style: 'currency', currency: item.currency || 'USD' }).format(item.price_numeric) : 'Precio no disponible';
        const reviewsText = item.reviews_count > 0 ? `⭐ ${item.rating || '?'} (${item.reviews_count})` : 'Sin reseñas';
        textContent.innerHTML = `${categoryHTML}<span class="item-title">${item.title || 'Título no disponible'}</span><div class="item-details"><span class="item-price">${formattedPrice}</span><span class="store-name">${item.source || 'Tienda'}</span></div><span class="item-reviews">${reviewsText}</span>`;
        a.appendChild(textContent); li.appendChild(a); return li;
    };

    // --- Iniciar la aplicación ---
    initialize();
});