document.addEventListener('DOMContentLoaded', () => {
    const statusText = document.getElementById('status-text');
    const linksList = document.getElementById('links-list');
    const description = document.querySelector('.description');

    const tiendas = [
        { nombre: "Mercado Libre AR", url: "https://listado.mercadolibre.com.ar/" },
        { nombre: "Amazon US", url: "https://www.amazon.com/s?k=" },
        { nombre: "AliExpress", url: "https://www.aliexpress.com/wholesale?SearchText=" }
    ];

    chrome.storage.local.get(['lastSearchQuery'], result => {
        const query = result.lastSearchQuery;
        if (query) {
            statusText.style.display = 'none';
            description.textContent = `Resultados para: "${query}"`;

            tiendas.forEach(tienda => {
                let searchUrl;
                if (tienda.nombre === "Mercado Libre AR") {
                    searchUrl = `${tienda.url}${query.replace(/\s+/g, '-')}`;
                } else {
                    searchUrl = `${tienda.url}${encodeURIComponent(query)}`;
                }
                
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = searchUrl;
                a.textContent = `Buscar en ${tienda.nombre}`;
                a.target = '_blank';
                
                li.appendChild(a);
                linksList.appendChild(li);
            });
        } else {
            description.style.display = 'none';
            statusText.textContent = 'Realiza una búsqueda en Google para ver los enlaces.';
        }
    });
});

