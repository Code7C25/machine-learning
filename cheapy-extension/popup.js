document.addEventListener('DOMContentLoaded', () => {
    // Referencias a los elementos del HTML
    const statusText = document.getElementById('status-text');
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');
    const showAllButton = document.getElementById('show-all-button');

    // Variable global para guardar todos los resultados
    let allResults = [];

    const performSearch = () => {
        chrome.storage.local.get(['lastSearchQuery'], result => {
            const query = result.lastSearchQuery;
            if (!query) {
                statusText.textContent = "Busca algo en Google para empezar.";
                return;
            }

            description.textContent = `Recomendaciones para: "${query}"`;
            statusText.textContent = 'Analizando las mejores ofertas...';
            
            const apiUrl = `http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}`;
            
            fetch(apiUrl)
                .then(response => response.json())
                .then(data => {
                    statusText.style.display = 'none';
                    
                    if (data.results && data.results.length > 0) {
                        allResults = data.results; // Guardamos todos los resultados
                        displayRecommendations(); // Mostramos solo las recomendaciones
                        showAllButton.style.display = 'block'; // Mostramos el botón
                    } else {
                        statusText.style.display = 'block';
                        statusText.textContent = data.message || "No se encontraron resultados.";
                    }
                })
                .catch(err => {
                    console.error(err);
                    statusText.style.display = 'block';
                    statusText.textContent = "Error al conectar con el backend.";
                });
        });
    };

    // Función para crear una tarjeta de resultado
    const createResultCard = (item, categoryInfo = {}) => {
        const li = document.createElement('li');
        const card = document.createElement('div');
        card.className = 'result-card';
        
        const a = document.createElement('a');
        a.href = item.url;
        a.target = '_blank';

        const stars = '⭐'.repeat(item.reliability_score || 0).padEnd(5, '☆');
        const reviewsText = item.reviews_count > 0 ? `(${item.reviews_count} reseñas)` : '';
        
        let categoryHTML = '';
        if (categoryInfo.title) {
            categoryHTML = `<span class="category-title ${categoryInfo.className || ''}">${categoryInfo.title}</span>`;
        }

        a.innerHTML = `
            ${categoryHTML}
            <span class="item-title">${item.title}</span>
            <span class="item-details">${item.price} | Confianza: ${stars} ${reviewsText}</span>
        `;
        
        card.appendChild(a);
        li.appendChild(card);
        return li;
    };

    // Función para mostrar solo las 2 recomendaciones
    const displayRecommendations = () => {
        linksList.innerHTML = "";

        // Lógica para encontrar los "ganadores" aquí en el frontend
        const masBarato = [...allResults].sort((a, b) => a.price_numeric - b.price_numeric)[0];
        
        const confiables = allResults.filter(p => p.reviews_count > 20 && p.reliability_score >= 4);
        let mejorCalidadPrecio = null;
        if (confiables.length > 0) {
            mejorCalidadPrecio = confiables.sort((a, b) => a.price_numeric - b.price_numeric)[0];
        } else {
            mejorCalidadPrecio = [...allResults].sort((a, b) => b.reviews_count - a.reviews_count)[0];
        }

        linksList.appendChild(createResultCard(masBarato, { title: "🔥 Más Barato" }));

        // Solo mostrar el segundo si es un producto diferente
        if (mejorCalidadPrecio && mejorCalidadPrecio.url !== masBarato.url) {
            linksList.appendChild(createResultCard(mejorCalidadPrecio, { title: "💎 Mejor Calidad-Precio", className: 'best-value' }));
        }
    };
    
    // Función para mostrar TODOS los resultados
    const displayAllResults = () => {
        linksList.innerHTML = "";
        allResults.forEach(item => {
            linksList.appendChild(createResultCard(item));
        });
        showAllButton.textContent = "Mostrar solo recomendaciones";
    };

    // Event listener para el botón
    showAllButton.addEventListener('click', () => {
        if (showAllButton.textContent.includes("Ver todos")) {
            displayAllResults();
        } else {
            displayRecommendations();
            showAllButton.textContent = "Ver todos los resultados";
        }
    });

    // Iniciar la búsqueda
    performSearch();
});