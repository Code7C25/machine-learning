document.addEventListener('DOMContentLoaded', () => {
    // Referencias a los elementos
    const resultsContainer = document.getElementById('results-container');
    const statusMessage = document.getElementById('status-message');
    const sortSelect = document.getElementById('sort-select');
    const showAllButton = document.getElementById('show-all-button');
    const recommendationsSection = document.getElementById('recommendations');
    const queryTitle = document.getElementById('query-title');
    const backToRecommendationsButton = document.getElementById('back-to-recommendations-button');

    let allResults = [];

    // --- LÓGICA INICIAL ---
    const initialize = () => {
        chrome.storage.local.get(['lastSearchQuery'], (result) => {
            const query = result.lastSearchQuery;
            if (query) {
                queryTitle.textContent = `Resultados para: "${query}"`;
                performSearch(query);
            } else {
                statusMessage.textContent = 'Realiza una búsqueda en Google para empezar.';
                queryTitle.textContent = 'Cheapy';
            }
        });
    };

    // --- MANEJADORES DE EVENTOS ---
    sortSelect.addEventListener('change', () => {
        displayAllResults();
    });

    showAllButton.addEventListener('click', () => {
        showAllView();
    });

    backToRecommendationsButton.addEventListener('click', () => {
        showRecommendationsView();
    });
    
    // --- FUNCIONES PARA CONTROLAR LA VISIBILIDAD DE LA UI ---
    const showLoadingState = (query) => {
        statusMessage.textContent = `Analizando "${query}"...`;
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
        resultsContainer.style.display = 'none'; // Ocultar la lista completa
        showAllButton.style.display = 'block';   // Mostrar botón para ver todo
        sortSelect.style.display = 'none';
        backToRecommendationsButton.style.display = 'none';
    };

    const showAllView = () => {
        statusMessage.style.display = 'none';
        recommendationsSection.style.display = 'none';
        resultsContainer.style.display = 'block'; // Mostrar la lista completa
        showAllButton.style.display = 'none';
        sortSelect.style.display = 'block';       // Mostrar el <select>
        backToRecommendationsButton.style.display = 'block';
        displayAllResults();
    };

    // --- FUNCIÓN DE BÚSQUEDA ---
    const performSearch = async (query) => {
        showLoadingState(query); // 1. Mostrar estado de carga
        allResults = [];

        try {
            // 2. Hacer la petición a la URL CORRECTA
            const response = await fetch(`http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}`);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                const detail = errorData?.detail || `Error del servidor: ${response.status}`;
                throw new Error(detail);
            }

            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                allResults = data.results;
                displayRecommendations(); // 3. Mostrar recomendaciones solo DESPUÉS de obtener resultados
            } else {
                statusMessage.textContent = 'No se encontraron resultados.';
            }
        } catch (error) {
            console.error('Error en la búsqueda:', error);
            statusMessage.textContent = `Error de conexión: ${error.message}.`;
        }
    };
    
    // --- FUNCIONES DE RENDERIZADO ---
    const displayRecommendations = () => {
        recommendationsSection.innerHTML = ''; // Limpiar
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
        showRecommendationsView(); // Ahora sí, cambiamos a la vista de recomendaciones
    };

    const displayAllResults = () => {
        resultsContainer.innerHTML = ''; // Limpiar
        const sortedResults = [...allResults];
        const sortBy = sortSelect.value;

        if (sortBy === 'price_asc') sortedResults.sort((a, b) => a.price_numeric - b.price_numeric);
        else if (sortBy === 'price_desc') sortedResults.sort((a, b) => b.price_numeric - a.price_numeric);
        else if (sortBy === 'reviews') sortedResults.sort((a, b) => b.reviews_count - a.reviews_count);
        
        sortedResults.forEach(item => resultsContainer.appendChild(createResultCard(item)));
    };

    const createResultCard = (item, categoryInfo = {}) => {
        if (!item) return document.createDocumentFragment(); // No crear tarjeta si el item es nulo
        
        const li = document.createElement('li'); li.className = 'result-card';
        const a = document.createElement('a'); a.href = item.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.className = 'result-card-link';
        const img = document.createElement('img'); img.src = item.image_url || 'icons/placeholder.png'; img.alt = item.title; img.className = 'result-image'; img.loading = 'lazy'; a.appendChild(img);
        const textContent = document.createElement('div'); textContent.className = 'result-text-content';
        let categoryHTML = ''; if (categoryInfo.label) { categoryHTML = `<span class="category-badge ${categoryInfo.className}">${categoryInfo.label}</span>`; }
        const formattedPrice = item.price_numeric ? new Intl.NumberFormat('es-AR', { style: 'currency', currency: item.currency || 'ARS' }).format(item.price_numeric) : 'Precio no disponible';
        const reviewsText = item.reviews_count > 0 ? `⭐ ${item.rating || '?'} (${item.reviews_count})` : 'Sin reseñas';
        // Corrección de error de sintaxis en el innerHTML
        textContent.innerHTML = `
            ${categoryHTML}
            <span class="item-title">${item.title || 'Título no disponible'}</span>
            <div class="item-details">
                <span class="item-price">${formattedPrice}</span>
                <span class="store-name">${item.source || 'Tienda'}</span>
            </div>
            <span class="item-reviews">${reviewsText}</span>
        `;
        a.appendChild(textContent); li.appendChild(a); return li;
    };

    // Iniciar la aplicación
    initialize();
});