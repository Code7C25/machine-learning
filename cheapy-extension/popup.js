document.addEventListener('DOMContentLoaded', () => {
    // --- 1. Referencias a los Elementos del HTML ---
    const statusText = document.getElementById('status-text');
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');
    
    // Referencias a los filtros
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    const reliabilitySlider = document.getElementById('reliability');
    const reliabilityValueSpan = document.getElementById('reliability-value');
    const filterButton = document.getElementById('filter-button');

    // --- 2. Lógica de la Interfaz ---
    // Actualiza el número de la confianza mientras se mueve el slider
    reliabilitySlider.addEventListener('input', () => {
        reliabilityValueSpan.textContent = reliabilitySlider.value;
    });

    // La función principal que se conecta al backend
    const performSearch = () => {
        chrome.storage.local.get(['lastSearchQuery'], result => {
            const query = result.lastSearchQuery;

            if (!query) {
                statusText.textContent = "Primero, busca algo en Google.";
                return;
            }

            // Preparamos la UI para la búsqueda
            description.textContent = `Resultados para: "${query}"`;
            statusText.textContent = 'Buscando y filtrando...';
            statusText.style.display = 'block';
            linksList.innerHTML = ''; // Limpiamos resultados anteriores
            
            // --- 3. Leer Filtros y Construir la URL ---
            const minPrice = minPriceInput.value;
            const maxPrice = maxPriceInput.value;
            const minReliability = reliabilitySlider.value;
            
            let apiUrl = `http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}`;
            
            if (minPrice) apiUrl += `&min_price=${minPrice}`;
            if (maxPrice) apiUrl += `&max_price=${maxPrice}`;
            // Solo enviamos el filtro de confiabilidad si no es el mínimo (1)
            if (minReliability > 1) apiUrl += `&min_reliability=${minReliability}`;
            
            // --- 4. Llamada a la API con fetch ---
            fetch(apiUrl)
                .then(response => {
                    if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    statusText.style.display = 'none'; // Ocultamos el "cargando..."
                    
                    if (data.results && data.results.length > 0) {
                        displayResults(data.results);
                    } else {
                        statusText.style.display = 'block';
                        statusText.textContent = data.message || "No se encontraron resultados.";
                    }
                })
                .catch(err => {
                    console.error("Error al conectar con el backend:", err);
                    statusText.style.display = 'block';
                    statusText.textContent = "Error al conectar con el backend. ¿Está encendido?";
                });
        });
    };

    // --- 5. Función Auxiliar para Mostrar Resultados ---
    const displayResults = (results) => {
        linksList.innerHTML = "";

        results.forEach(item => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            
            a.href = item.url;
            
            // --- LÍNEA MODIFICADA PARA MOSTRAR EL NÚMERO DE RESEÑAS/VENTAS ---
            const stars = '⭐'.repeat(item.reliability_score).padEnd(5, '☆');
            const reviewsText = item.reviews_count > 0 ? `(${item.reviews_count} reseñas)` : '';
            
            a.textContent = `${item.title} — ${item.price} [${item.source}] | Confianza: ${stars} ${reviewsText}`;
            a.target = '_blank';
            
            li.appendChild(a);
            linksList.appendChild(li);
        });
    };

    // --- 6. Event Listeners ---
    // El botón "Buscar y Filtrar" ahora es el que inicia todo
    filterButton.addEventListener('click', performSearch);
    
    // También, realizamos una búsqueda inicial con filtros por defecto cuando se abre el popup
    performSearch();
});