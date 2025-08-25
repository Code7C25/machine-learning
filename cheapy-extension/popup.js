document.addEventListener('DOMContentLoaded', () => {
    // --- Referencias a los elementos del HTML ---
    const statusText = document.getElementById('status-text');
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');
    
    // Referencias a los nuevos filtros
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    const reliabilitySlider = document.getElementById('reliability');
    const reliabilityValueSpan = document.getElementById('reliability-value');
    const filterButton = document.getElementById('filter-button');

    // --- Lógica para actualizar el valor del slider en la UI ---
    reliabilitySlider.addEventListener('input', () => {
        reliabilityValueSpan.textContent = reliabilitySlider.value;
    });

    // --- Función Principal de Búsqueda ---
    const performSearch = () => {
        // Obtenemos la última búsqueda guardada por background.js
        chrome.storage.local.get(['lastSearchQuery'], result => {
            const query = result.lastSearchQuery;

            if (!query) {
                statusText.textContent = "Realiza una búsqueda en Google para ver los precios.";
                return;
            }

            // Actualizamos la UI
            description.textContent = `Resultados para: "${query}"`;
            statusText.textContent = 'Buscando y filtrando precios...';
            statusText.style.display = 'block';
            linksList.innerHTML = '';
            
            // Leemos los valores de los filtros desde la UI
            const minPrice = minPriceInput.value;
            const maxPrice = maxPriceInput.value;
            const minReliability = reliabilitySlider.value;
            
            // Construimos la URL de la API dinámicamente
            let apiUrl = `http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}`;
            
            if (minPrice) apiUrl += `&min_price=${minPrice}`;
            if (maxPrice) apiUrl += `&max_price=${maxPrice}`;
            if (minReliability > 1) apiUrl += `&min_reliability=${minReliability}`;
            
            // Hacemos la llamada a nuestra API
            fetch(apiUrl)
                .then(response => {
                    if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    statusText.style.display = 'none';
                    
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

    // --- Función para Mostrar los Resultados ---
    const displayResults = (results) => {
        linksList.innerHTML = ""; // Limpiamos la lista

        results.forEach(item => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        
        a.href = item.url;
        // --- TEXTO MEJORADO ---
        // Mostramos estrellas en lugar de un número
        const stars = '⭐'.repeat(item.reliability_score).padEnd(5, '☆'); // Ej: ⭐⭐⭐☆☆
        a.textContent = `${item.title} — ${item.price} [${item.source}] (Confianza: ${stars})`;
        
        a.target = '_blank';
        
        li.appendChild(a);
        linksList.appendChild(li);
    });
    };

    // --- Event Listeners ---
    // 1. Cuando se hace clic en el botón "Filtrar"
    filterButton.addEventListener('click', performSearch);
    
    // 2. Ejecutamos una búsqueda inicial automáticamente cuando se abre el popup
    performSearch();
});