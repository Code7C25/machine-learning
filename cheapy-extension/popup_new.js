/**
 * Cheapy Chrome Extension Popup Script
 *
 * Handles the user interface for the Cheapy price comparison extension.
 * Manages search initiation, result polling, and result display with
 * sorting and filtering capabilities.
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
     * Controls view switching between different UI states.
     * @param {string} viewName - The view to display ('loading', 'recommendations', 'all')
     */
    const switchView = (viewName) => {
        // Hide all main containers to start with clean state
        statusMessage.style.display = 'none';
        recommendationsView.style.display = 'none';
        allResultsView.style.display = 'none';

        // Show only the container corresponding to current view
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
     * Retrieves user's country with local storage caching.
     * Uses ip-api.com for geolocation with 24-hour cache validity.
     * @returns {Promise<string>} Country code (e.g., 'AR', 'US')
     */
    const getUserCountry = async () => {
        try {
            const cache = await chrome.storage.local.get(['userCountry', 'countryCacheTimestamp']);
            const now = new Date().getTime();

            // Use cache if valid (less than 24 hours old)
            if (cache.userCountry && cache.countryCacheTimestamp &&
                (now - cache.countryCacheTimestamp < 86400000)) {
                console.log("Country from extension cache:", cache.userCountry);
                return cache.userCountry;
            }

            // Fetch from API if no valid cache exists
            console.log("Calling geolocation API from extension...");
            const response = await fetch("http://ip-api.com/json/?fields=countryCode");
            if (!response.ok) return "AR"; // Fallback to Argentina

            const data = await response.json();
            const country = data.countryCode || "AR";

            // Cache the result
            await chrome.storage.local.set({
                userCountry: country,
                countryCacheTimestamp: now
            });
            console.log("Country saved to extension cache:", country);
            return country;
        } catch (error) {
            console.error("Geolocation error from frontend:", error);
            return "AR"; // Fallback on error
        }
    };

    /**
     * Initializes the extension popup.
     * Retrieves last search query and user's country, then performs search if available.
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
     * Initiates product search by calling the backend API.
     * @param {string} query - Search query string
     * @param {string} country - User's country code
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
     * Polls backend for search results completion.
     * @param {string} taskId - Task ID from search initiation
     * @param {number} attempt - Current polling attempt number
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
            } else { // PENDING
                statusMessage.textContent = `Procesando... (${resultData.completed || '0/?'})`;
                setTimeout(() => pollForResult(taskId, attempt + 1), 2000);
            }
        } catch (error) {
            statusMessage.textContent = `Error al verificar resultados: ${error.message}`;
            switchView('loading');
        }
    };

    // Event listeners for UI controls
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
     * Displays top recommendations (cheapest and best value products).
     */
    const displayRecommendations = () => {
        recommendationsSection.innerHTML = '';

        // Find cheapest product prioritizing similarity
        const cheapest = [...allResults].sort((a, b) => {
            const simA = a.similarity_score || 0;
            const simB = b.similarity_score || 0;
            if (simB !== simA) return simB - simA;
            return a.price_numeric - b.price_numeric;
        })[0];

        // Find best value product (high rating/reviews, prioritizing similarity)
        const bestValue = [...allResults]
            .filter(item => item.reviews_count > 0)
            .sort((a, b) => {
                const simA = a.similarity_score || 0;
                const simB = b.similarity_score || 0;
                if (simB !== simA) return simB - simA;
                if (b.rating - a.rating !== 0) return b.rating - a.rating;
                return b.reviews_count - a.reviews_count;
            })[0] || cheapest;

        // Display recommendation cards
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
     * Displays all search results with sorting and filtering options.
     */
    const displayAllResults = () => {
        resultsContainer.innerHTML = '';
        const sortedResults = [...allResults];
        const sortBy = sortSelect.value;
        const similarityChecked = similarityCheckbox.checked;

        sortedResults.sort((a, b) => {
            // Prioritize similarity if checkbox is checked
            if (similarityChecked) {
                const simA = a.similarity_score || 0;
                const simB = b.similarity_score || 0;
                if (simB !== simA) return simB - simA;
            }

            // Extract comparison values
            const priceA = a.price_numeric ?? Infinity;
            const priceB = b.price_numeric ?? Infinity;
            const reviewsA = a.reviews_count ?? 0;
            const reviewsB = b.reviews_count ?? 0;
            const ratingA = a.rating ?? 0;
            const ratingB = b.rating ?? 0;

            // Calculate discount percentages
            const discA = (typeof a.discount_percent === 'number') ? a.discount_percent :
                (a.price_before_numeric && a.price_numeric ?
                    Math.max(0, ((a.price_before_numeric - a.price_numeric) / a.price_before_numeric) * 100) : 0);
            const discB = (typeof b.discount_percent === 'number') ? b.discount_percent :
                (b.price_before_numeric && b.price_numeric ?
                    Math.max(0, ((b.price_before_numeric - b.price_numeric) / b.price_before_numeric) * 100) : 0);

            // Apply selected sorting criteria
            switch (sortBy) {
                case 'price_asc': return priceA - priceB;
                case 'price_desc': return priceB - priceA;
                case 'reviews': return reviewsB - reviewsA;
                case 'deal_desc':
                    // Sort by deals first, then by discount percentage
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
     * Creates a result card element for a product item.
     * @param {Object} item - Product data object
     * @param {Object} categoryInfo - Optional category badge info
     * @returns {HTMLElement} Result card element
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

        // Use chrome.tabs.create to open links without activating new tab
        a.addEventListener('click', (event) => {
            event.preventDefault();
            chrome.tabs.create({
                url: item.url,
                active: false // Keep focus on current tab
            });
        });

        // Create image element
        const img = document.createElement('img');
        img.src = item.image_url || 'icons/placeholder.png';
        img.alt = item.title;
        img.className = 'result-image';
        img.loading = 'lazy';
        a.appendChild(img);

        // Create text content container
        const textContent = document.createElement('div');
        textContent.className = 'result-text-content';

        // Add category badge if provided
        let categoryHTML = '';
        if (categoryInfo.label) {
            categoryHTML = `<span class="category-badge ${categoryInfo.className}">${categoryInfo.label}</span>`;
        }

        // Format price display
        const formattedPriceNumeric = item.price_numeric ?
            new Intl.NumberFormat(undefined, {
                style: 'currency',
                currency: item.currency || 'USD'
            }).format(item.price_numeric) : null;

        // Prefer backend's cleaned price display
        const rawPrice = item.price_display ?
            String(item.price_display).trim() :
            (item.price ? String(item.price).trim() : null);

        // Build price HTML with discount handling
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

        // Build reviews text
        const reviewsText = item.reviews_count > 0 ?
            `⭐ ${item.rating || '?'} (${item.reviews_count})` : 'Sin reseñas';

        // Assemble text content HTML
        textContent.innerHTML = `${categoryHTML}<span class="item-title">${item.title || 'Título no disponible'}</span><div class="item-details">${priceHTML}<span class="store-name">${item.source || 'Tienda'}</span></div><span class="item-reviews">${reviewsText}</span>`;

        a.appendChild(textContent);
        li.appendChild(a);
        return li;
    };

    // Initialize the application
    initialize();
});