/**
 * Cheapy Chrome Extension Popup Script
 *
 * Gestiona la interfaz de usuario de la extensión de comparación de precios Cheapy.
 * Maneja la iniciación de búsquedas, la consulta de resultados y la visualización de resultados con capacidades de ordenación y filtrado.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM element references for UI manipulation
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

    /**
     * Controls la conmutación de vistas entre diferentes estados de la interfaz de usuario.
     * @param {string} viewName - La vista a mostrar ('loading', 'recommendations', 'all')
     */
    const switchView = (viewName) => {
        // Oculte todos los contenedores principales para comenzar con el estado limpio
        statusMessage.style.display = 'none';
        recommendationsView.style.display = 'none';
        allResultsView.style.display = 'none';

        // Mostrar solo el contenedor correspondiente a la vista actual
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
            default:
                statusMessage.style.display = 'block';
                break;
        }
    };

    /**
     * Recupera el país del usuario con almacenamiento en caché local.
     * Utiliza ip-api.com para geolocalización con validez de caché de 24 horas.
     * @returns {Promise<string>} Código de país (por ejemplo, 'AR', 'US')
     */
    const getUserCountry = async () => {
        try {
            const cache = await chrome.storage.local.get(['userCountry', 'countryCacheTimestamp']);
            const now = new Date().getTime();

            // Utilice caché si es válido (menos de 24 horas)
            if (cache.userCountry && cache.countryCacheTimestamp &&
                (now - cache.countryCacheTimestamp < 86400000)) {
                console.log("Country from extension cache:", cache.userCountry);
                return cache.userCountry;
            }

            // Obtenga datos de la API si no existe caché válida
            console.log("Llamando a la API de geolocalización desde la extensión...");
            const response = await fetch("http://ip-api.com/json/?fields=countryCode");
            if (!response.ok) return "AR"; // Valor predeterminado a Argentina

            const data = await response.json();
            const country = data.countryCode || "AR";

            // Cache the result
            await chrome.storage.local.set({
                userCountry: country,
                countryCacheTimestamp: now
            });
            console.log("País guardado en la caché de la extensión:", country);
            return country;
        } catch (error) {
            console.error("Error de geolocalización desde el frontend:", error);
            return "AR"; // Respaldo en caso de error
        }
    };

    /**
     * Inicializa el popup de la extensión.
     * Recupera la última consulta de búsqueda y el país del usuario, luego realiza la búsqueda si está disponible.
     */
    const initialize = async () => {
        const country = await getUserCountry();

        chrome.storage.local.get(['lastSearchQuery'], (result) => {
            const query = result.lastSearchQuery;
            if (query) {
                queryTitle.textContent = `Resultados para: "${query}"`;
                performSearch(query, country);
            } else {
                queryTitle.textContent = 'Cheapy';
                statusMessage.textContent = 'Realiza una búsqueda en Google para empezar.';
                switchView('loading');
            }
        });
    };

    /**
     * Inicia la búsqueda de productos llamando a la API del backend.
     * @param {string} query - Cadena de consulta de búsqueda
     * @param {string} country - Código de país del usuario
     */
    const performSearch = async (query, country) => {
        statusMessage.textContent = `Analizando "${query}"...`;
        switchView('loading');

        try {
            const searchResponse = await fetch(
                `http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}&country=${country}`
            );
            if (!searchResponse.ok) throw new Error("Error al iniciar la búsqueda.");

            const taskData = await searchResponse.json();
            if (taskData.error) {
                throw new Error(taskData.error);
            }
            if (taskData.task_id) {
                pollForResult(taskData.task_id);
            } else {
                throw new Error("No se recibió un ID de tarea.");
            }
        } catch (error) {
            statusMessage.textContent = `Error de conexión: ${error.message}`;
        }
    };

    /**
     * Consulta al backend para la finalización de los resultados de búsqueda.
     * @param {string} taskId - ID de tarea desde el inicio de la búsqueda
     * @param {number} attempt - Número actual de intento de sondeo
     */
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
            } else { // PENDIENTE
                statusMessage.textContent = `Procesando... (${resultData.completed || '0/?'})`;
                setTimeout(() => pollForResult(taskId, attempt + 1), 2000);
            }
        } catch (error) {
            statusMessage.textContent = `Error al verificar resultados: ${error.message}`;
            switchView('loading');
        }
    };

    // Oyentes de eventos para controles de UI
    sortSelect.addEventListener('change', () => displayAllResults());
    similarityCheckbox.addEventListener('change', () => displayAllResults());

    showAllButton.addEventListener('click', () => {
        switchView('all');
        displayAllResults();
    });

    backToRecommendationsButton.addEventListener('click', () => {
        switchView('recommendations');
    });

    /**
     * Muestra las principales recomendaciones (productos más baratos y mejor relación calidad-precio).
     */
    const displayRecommendations = () => {
        recommendationsSection.innerHTML = '';

        // Encuentra el producto más barato priorizando la similitud
        const cheapest = [...allResults].sort((a, b) => {
            const simA = a.similarity_score || 0;
            const simB = b.similarity_score || 0;
            if (simB !== simA) return simB - simA;
            return a.price_numeric - b.price_numeric;
        })[0];

        // Encuentra el producto con mejor relación calidad-precio (alta calificación/reseñas, priorizando similitud)
        const bestValue = [...allResults]
            .filter(item => item.reviews_count > 0)
            .sort((a, b) => {
                const simA = a.similarity_score || 0;
                const simB = b.similarity_score || 0;
                if (simB !== simA) return simB - simA;
                if (b.rating - a.rating !== 0) return b.rating - a.rating;
                return b.reviews_count - a.reviews_count;
            })[0] || cheapest;

        // Muestra las tarjetas de recomendación
        if (cheapest) {
            recommendationsSection.appendChild(
                createResultCard(cheapest, { label: 'Más Barato', className: 'cheapest' })
            );
        }
        if (bestValue && (!cheapest || cheapest.url !== bestValue.url)) {
            recommendationsSection.appendChild(
                createResultCard(bestValue, { label: 'Mejor Calidad-Precio', className: 'best-value' })
            );
        }

        showAllButton.textContent = `Ver los ${allResults.length} resultados`;
        switchView('recommendations');
    };

    /**
     * Muestra todos los resultados de búsqueda con opciones de ordenación y filtrado.
     */
    const displayAllResults = () => {
        resultsContainer.innerHTML = '';
        const sortedResults = [...allResults];
        const sortBy = sortSelect.value;
        const similarityChecked = similarityCheckbox.checked;

        sortedResults.sort((a, b) => {
            // Prioriza la similitud si la casilla está marcada
            if (similarityChecked) {
                const simA = a.similarity_score || 0;
                const simB = b.similarity_score || 0;
                if (simB !== simA) return simB - simA;
            }

            // Extrae valores para comparación
            const priceA = a.price_numeric ?? Infinity;
            const priceB = b.price_numeric ?? Infinity;
            const reviewsA = a.reviews_count ?? 0;
            const reviewsB = b.reviews_count ?? 0;
            const ratingA = a.rating ?? 0;
            const ratingB = b.rating ?? 0;

            // Calcula los porcentajes de descuento
            const discA = (typeof a.discount_percent === 'number') ? a.discount_percent :
                (a.price_before_numeric && a.price_numeric ?
                    Math.max(0, ((a.price_before_numeric - a.price_numeric) / a.price_before_numeric) * 100) : 0);
            const discB = (typeof b.discount_percent === 'number') ? b.discount_percent :
                (b.price_before_numeric && b.price_numeric ?
                    Math.max(0, ((b.price_before_numeric - b.price_numeric) / b.price_before_numeric) * 100) : 0);

            // Aplica los criterios de ordenación seleccionados
            switch (sortBy) {
                case 'price_asc': return priceA - priceB;
                case 'price_desc': return priceB - priceA;
                case 'reviews': return reviewsB - reviewsA;
                case 'deal_desc':
                    // Ordena por ofertas primero, luego por porcentaje de descuento
                    if ((b.on_sale === true) !== (a.on_sale === true)) {
                        return (b.on_sale === true) ? 1 : -1;
                    }
                    return (discB || 0) - (discA || 0);
                case 'relevance':
                default:
                    if (ratingB !== ratingA) { return ratingB - ratingA; }
                    return reviewsB - reviewsA;
            }
        });

        sortedResults.forEach(item => resultsContainer.appendChild(createResultCard(item)));
    };

    /**
     * crea un elemento de tarjeta de resultados para un artículo de producto. *@param {Objeto} elemento -Objeto de datos del producto *@param {Objeto} categoríaInfo -Información de insignia de categoría opcional
     * @returns {HTMLElement} Elemento de tarjeta de resultado
     */
    const createResultCard = (item, categoryInfo = {}) => {
        if (!item) return document.createDocumentFragment();

        const li = document.createElement('li');
        li.className = 'result-card';

        const a = document.createElement('a');
        a.href = item.url;
        a.rel = 'noopener noreferrer';
        a.className = 'result-card-link';
        a.target = '_blank';

        // Usa chrome.tabs.create para abrir enlaces sin activar una nueva pestaña
        a.addEventListener('click', (event) => {
            event.preventDefault();
            chrome.tabs.create({
                url: item.url,
                active: false // Mantener el foco en la pestaña actual
            });
        });

        // Crea el elemento de imagen
        const img = document.createElement('img');
        img.src = item.image_url || 'icons/placeholder.png';
        img.alt = item.title;
        img.className = 'result-image';
        img.loading = 'lazy';
        a.appendChild(img);

        // Crea el contenedor de contenido de texto
        const textContent = document.createElement('div');
        textContent.className = 'result-text-content';

        // Añade la insignia de categoría si se proporciona
        let categoryHTML = '';
        if (categoryInfo.label) {
            categoryHTML = `<span class="category-badge ${categoryInfo.className}">${categoryInfo.label}</span>`;
        }

        // Formatea la visualización del precio
        const formattedPriceNumeric = item.price_numeric ?
            new Intl.NumberFormat(undefined, {
                style: 'currency',
                currency: item.currency || 'USD'
            }).format(item.price_numeric) : null;

        // Prefiere la visualización de precio limpia del backend
        const rawPrice = item.price_display ?
            String(item.price_display).trim() :
            (item.price ? String(item.price).trim() : null);

        // Construye el HTML del precio con manejo de descuento
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

        // Construye el texto de reseñas
        const reviewsText = item.reviews_count > 0 ?
            `⭐ ${item.rating || '?'} (${item.reviews_count})` : 'Sin reseñas';

        // Ensambla el HTML del contenido de texto
        textContent.innerHTML = `${categoryHTML}<span class="item-title">${item.title || 'Título no disponible'}</span><div class="item-details">${priceHTML}<span class="store-name">${item.source || 'Tienda'}</span></div><span class="item-reviews">${reviewsText}</span>`;

        a.appendChild(textContent);
        li.appendChild(a);
        return li;
    };

    // Inicializa la aplicación
    initialize();
});