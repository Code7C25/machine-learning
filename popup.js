const tiendas = [
    { nombre: "Mercado Libre", url: "https://www.mercadolibre.com.ar/" },
    { nombre: "Amazon", url: "https://www.amazon.com/" },
    { nombre: "AliExpress", url: "https://www.aliexpress.com/" }
];

const ul = document.getElementById("tiendas");

tiendas.forEach(tienda => {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${tienda.url}" target="_blank">${tienda.nombre}</a>`;
    ul.appendChild(li);
});

