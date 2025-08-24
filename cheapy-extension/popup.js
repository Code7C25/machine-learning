document.addEventListener('DOMContentLoaded', () => {
    const statusText = document.getElementById('status-text');
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');

    // Muestra un mensaje de carga inicial
    statusText.textContent = 'Buscando precios...';
    linksList.innerHTML = '';

    // Obtenemos la última búsqueda guardada por background.js
    chrome.storage.local.get(['lastSearchQuery'], result => {
        const query = result.lastSearchQuery;

        if (query) {
            // Actualizamos la UI para mostrar qué se está buscando
            description.textContent = `Resultados para: "${query}"`;
            
            // Llamamos a nuestra API de backend
            fetch(`http://127.0.0.1:8000/buscar?q=${encodeURIComponent(query)}`)
                .then(response => {
                    // Verificamos si la respuesta del servidor es exitosa
                    if (!response.ok) {
                        throw new Error(`Error del servidor: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Ocultamos el texto de estado
                    statusText.style.display = 'none';
                    
                    // --- AQUÍ ESTÁN LOS CAMBIOS PRINCIPALES ---
                    // Verificamos si el backend devolvió la propiedad 'results'
                    if (data.results && data.results.length > 0) {
                        
                        // Limpiamos la lista por si acaso
                        linksList.innerHTML = "";

                        // Iteramos sobre cada producto en el array 'results'
                        data.results.forEach(item => {
                            const li = document.createElement('li');
                            const a = document.createElement('a');
                            
                            // Usamos los nombres de campo correctos que devuelve el backend
                            a.href = item.url; // 'url' en lugar de 'link'
                            a.textContent = `${item.title} — ${item.price} [${item.source}]`; // 'title', 'price', 'source'
                            
                            a.target = '_blank'; // Para que se abra en una nueva pestaña
                            
                            li.appendChild(a);
                            linksList.appendChild(li);
                        });
                    } else {
                        // Si no hay resultados, mostramos el mensaje que nos da el backend
                        statusText.style.display = 'block';
                        statusText.textContent = data.message || "No se encontraron resultados.";
                    }
                })
                .catch(err => {
                    // Si hay un error de red o al conectar, lo mostramos
                    console.error("Error al conectar con el backend:", err);
                    statusText.style.display = 'block';
                    statusText.textContent = "Error al conectar con el backend. ¿Está encendido?";
                });
        } else {
            // Si el usuario aún no ha buscado nada en Google
            statusText.textContent = "Realiza una búsqueda en Google para ver los precios.";
        }
    });
});