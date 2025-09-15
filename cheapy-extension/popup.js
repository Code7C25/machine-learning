document.addEventListener('DOMContentLoaded', () => {
    const statusText = document.getElementById('status-text');
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');
    const showAllButton = document.getElementById('show-all-button');
    const sortContainer = document.getElementById('sort-container');
    const sortSelect = document.getElementById('sort-select');

    let allResults = [];

    const getNumericPrice = (priceStr) => {
        if (!priceStr || typeof priceStr !== 'string') return null;
        try {
            const cleaned = priceStr.replace(/[^\d,.]/g, '').replace(',', '.');
            return parseFloat(cleaned);
        } catch (e) {
            return null;
        }
    };

    const performSearch = () => {
        chrome.storage.local.get(['lastSearchQuery'], result => {
            const query = result.lastSearchQuery;
            if (!query) {
                statusText.textContent = "Busca algo en Google para empezar.";
                return;
            }
            description.textContent = `Recomendaciones para: "${query}"`;
            statusText.textContent = 'Analizando las mejores ofertas...';
            statusText.style.display = 'block'; // Aseguramos que se vea el mensaje de carga
            linksList.innerHTML = '';
            showAllButton.style.display = 'none'; // Ocultamos botones mientras carga
            sortContainer.style.display = 'none';
            
            const apiUrl = `http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}`;
            
            // --- LÓGICA DE FETCH MEJORADA ---
            fetch(apiUrl)
                .then(response => {
                    // Si la respuesta no es OK (ej. 404, 500, 504), la procesamos como un error
                    if (!response.ok) {
                        // Intentamos leer el JSON del error que envía FastAPI
                        return response.json().then(errorData => {
                            // Creamos un error con el mensaje específico del backend
                            throw new Error(errorData.detail || `Error del servidor: ${response.status}`);
                        }).catch(() => {
                            // Si el cuerpo del error no es JSON, lanzamos un error genérico
                            throw new Error(`Error del servidor: ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    statusText.style.display = 'none';
                    
                    // Si el backend devuelve un mensaje (ej. "no se encontraron resultados"), lo mostramos
                    if (data.message) {
                        statusText.textContent = data.message;
                        statusText.style.display = 'block';
                        return; // Terminamos la ejecución aquí
                    }

                    if (data.results && data.results.length > 0) {
                        allResults = data.results.map(item => ({
                            ...item,
                            price_numeric: getNumericPrice(item.price)
                        })).filter(item => item.price_numeric !== null);

                        displayRecommendations();
                        showAllButton.style.display = 'block';
                    } else {
                        // Caso de seguridad por si 'results' está vacío pero no hay 'message'
                        statusText.textContent = "No se encontraron productos.";
                        statusText.style.display = 'block';
                    }
                })
                .catch(err => {
                    console.error("Error capturado en fetch:", err);
                    statusText.textContent = err.message; // Mostramos el mensaje de error específico
                    statusText.style.display = 'block';
                });
        });
    };

    // (El resto de las funciones: createResultCard, displayRecommendations, displayAllResults y los Event Listeners se quedan exactamente igual)
    const createResultCard = (item, categoryInfo = {}) => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.className = 'result-card-link';
        a.href = item.url;
        a.target = '_blank';
        const img = document.createElement('img');
        img.className = 'product-image';
        img.src = item.image_url || 'icons/icon.png';
        a.appendChild(img);
        const textContent = document.createElement('div');
        textContent.className = 'text-content';
        const stars = '⭐'.repeat(item.reliability_score || 0).padEnd(5, '☆');
        const reviewsText = item.reviews_count > 0 ? `(${item.reviews_count} reseñas)` : '';
        let categoryHTML = '';
        if (categoryInfo.title) {
            categoryHTML = `<span class="category-title ${categoryInfo.className || ''}">${categoryInfo.title}</span>`;
        }
        textContent.innerHTML = `
            ${categoryHTML}
            <span class="item-title">${item.title}</span>
            <span class="item-details">${item.price} | ${stars} ${reviewsText}</span>
        `;
        a.appendChild(textContent);
        li.appendChild(a);
        return li;
    };
    
    const displayRecommendations = () => { /* ... sin cambios ... */ };
    const displayAllResults = () => { /* ... sin cambios ... */ };
    showAllButton.addEventListener('click', () => { /* ... sin cambios ... */ });
    sortSelect.addEventListener('change', displayAllResults);

    performSearch();
});

// Para evitar duplicar código, aquí están las funciones que no cambiaron
function displayRecommendations() {
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');
    const sortContainer = document.getElementById('sort-container');
    const showAllButton = document.getElementById('show-all-button');
    const allResults = window.allResults || [];

    linksList.innerHTML = "";
    description.textContent = "Recomendaciones para tu búsqueda:";
    sortContainer.style.display = 'none';
    showAllButton.textContent = "Ver todos los resultados";

    if (allResults.length === 0) return;

    const sortedByPrice = [...allResults].sort((a, b) => a.price_numeric - b.price_numeric);
    const masBarato = sortedByPrice[0];
    const confiables = allResults.filter(p => p.reviews_count > 20 && p.reliability_score >= 4);
    
    let mejorCalidadPrecio = null;
    if (confiables.length > 0) {
        mejorCalidadPrecio = confiables.sort((a, b) => a.price_numeric - b.price_numeric)[0];
    } else {
        mejorCalidadPrecio = [...allResults].sort((a, b) => b.reviews_count - a.reviews_count)[0];
    }

    linksList.appendChild(createResultCard(masBarato, { title: "🔥 Más Barato" }));
    if (mejorCalidadPrecio && mejorCalidadPrecio.url !== masBarato.url) {
        linksList.appendChild(createResultCard(mejorCalidadPrecio, { title: "💎 Mejor Calidad-Precio", className: 'best-value' }));
    }
}

function displayAllResults() {
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');
    const sortContainer = document.getElementById('sort-container');
    const showAllButton = document.getElementById('show-all-button');
    const sortSelect = document.getElementById('sort-select');
    const allResults = window.allResults || [];

    linksList.innerHTML = "";
    description.textContent = "Todos los resultados:";
    sortContainer.style.display = 'flex';
    showAllButton.textContent = "Mostrar solo recomendaciones";
    
    const sortBy = sortSelect.value;
    let sortedList = [...allResults]; 

    if (sortBy === 'price_asc') sortedList.sort((a, b) => a.price_numeric - b.price_numeric);
    else if (sortBy === 'price_desc') sortedList.sort((a, b) => b.price_numeric - a.price_numeric);
    else if (sortBy === 'reviews_desc') sortedList.sort((a, b) => b.reviews_count - a.reviews_count);

    sortedList.forEach(item => {
        linksList.appendChild(createResultCard(item));
    });
}
window.allResults = []; // Hacemos la variable global para que sea accesible