# cheapy-backend/cheapy_scraper/spiders/aliexpress_spider.py

import scrapy
from urllib.parse import urlencode, urlparse, urlunparse
from cheapy_scraper.items import ProductItem
# No necesitamos config.py para dominios, pero sí para la moneda si queremos ser precisos
from config import COUNTRY_CURRENCIES 

class AliexpressSpider(scrapy.Spider):
    name = "aliexpress"
    custom_settings = {
        'DOWNLOAD_HANDLERS': { "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler", "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler" },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': False  # <-- CAMBIO 1: Poner en False para ver el navegador
        }
    }
    
    # Ali usa el parámetro page=N
    
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Referer': 'https://www.google.com/',
    }

    def __init__(self, query="", country="AR", **kwargs):
        super().__init__(**kwargs)
        if not query:
            raise ValueError("El argumento 'query' es obligatorio.")
        
        self.query = query
        self.country_code = country.upper()
        # Nota: Ali express usa USD globalmente, pero podemos intentar obtener el tipo de moneda del país
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD') 
        
        # URL base de búsqueda con el query parameter 'SearchText'
        base_url = "https://www.aliexpress.com/wholesale"
        
        # Parámetros iniciales: Buscar por texto y establecer la página 1
        params = {
            'SearchText': self.query,
            'page': 1,
            'g': 'y' # A veces necesario para cargar la página de resultados
        }
        
        # Construye la URL inicial
        self.start_urls = [f"{base_url}?{urlencode(params)}"]
        self.current_page = 1 
        
        self.logger.info(f"Iniciando spider para AliExpress. Búsqueda: {self.query}")

    def normalize_url(self, url):
        """Remueve fragmentos y query strings de seguimiento de AliExpress."""
        if not url:
            return url
        
        # AliExpress usa URLs muy largas. Queremos quedarnos solo con el identificador del producto.
        parsed = urlparse(url)
        
        # Para Ali, la URL única es típicamente el path
        # Ejemplo: /item/100500123456.html
        return urlunparse(parsed._replace(query='', fragment=''))
    
    def parse(self, response):
        self.logger.info(f"Parseando página {self.current_page}/{self.MAX_PAGES} - {response.url}")

        # Intentamos obtener los contenedores de artículos, priorizando las clases comunes de Ali:
        # 1. Contenedor de la vista de lista/galería principal
        item_containers = response.css('div[data-spm="product_list"]') 
        if not item_containers:
            # 2. Selector genérico de la tarjeta del producto (más estable en la vista listado)
            item_containers = response.css('div.man-pc-search-item-card') 

        if not item_containers:
            # === CÓDIGO AÑADIDO PARA DEPURACIÓN ===
            filename = f'aliexpress_debug_page_{self.current_page}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                # response.text contiene el HTML renderizado por Playwright
                f.write(response.text)
            self.logger.critical(f"DEBUG: No se encontraron ítems. HTML guardado en {filename} para inspección.")
            # === FIN CÓDIGO DEPURACIÓN ===


        for item in item_containers:
            # --- 1. URL y Título ---
            # El enlace está generalmente asociado con el título o el wrapper de la tarjeta
            link = item.css('a.man-pc-search-item-card__title::attr(href)').get() or \
                   item.css('a::attr(href)').get() 
            
            if link and not link.startswith('http'):
                link = response.urljoin(link)
                
            title = item.css('a.man-pc-search-item-card__title::text').get() or \
                    item.css('div.man-pc-search-item-card__title::text').get()
            
            # 2. Precio
            # El precio actual suele estar en una clase que contiene la moneda y la fracción
            price_current = item.css('div.man-pc-search-item-card__price-current::text').get() or \
                            item.css('.price-current::text').get()
            
            # 3. Imagen
            # La imagen principal, asegurando obtener el 'src'
            image_url = item.css('img.man-pc-search-item-card__thumbnail-img::attr(src)').get()
            
            # 4. Reviews/Rating (Suelen estar muy escondidos, usamos lo más probable)
            rating_str = item.css('.man-pc-search-item-card__star-level::text').get()
            reviews_count_str = item.css('.man-pc-search-item-card__feedback::text').get()

            
            if not title or not link or not price_current:
                self.logger.debug(f"Saltando ítem incompleto. Título: {title}, Link: {link}, Precio: {price_current}")
                continue 

            # --- Creación y normalización del Ítem ---
            normalized_url = self.normalize_url(link)

            product = ProductItem()
            product['title'] = title.strip() if title else None
            product['url'] = normalized_url
            product['image_url'] = image_url
            product['source'] = self.name
            product['price'] = price_current.strip()
            product['rating_str'] = rating_str
            product['reviews_count_str'] = reviews_count_str
            product['currency_code'] = self.currency
            product['country_code'] = self.country_code
            yield product

        # --- Lógica de Paginación (Usando el parámetro 'page') ---
        if self.current_page < self.MAX_PAGES:
            self.current_page += 1
            
            # Parseamos la URL actual para manipular los parámetros
            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            
            # Establecemos el nuevo número de página
            query_params['page'] = [str(self.current_page)]
            
            # Reconstruimos la URL
            new_query = urlencode(query_params, doseq=True)
            next_page_url = urlunparse(parsed_url._replace(query=new_query, fragment=''))

            self.logger.info(f"Calculado: Próxima URL de AliExpress (Página {self.current_page})")

            yield scrapy.Request(
                url=next_page_url, 
                headers=self.custom_headers,
                callback=self.parse,
                meta={
                    'playwright': True,
                    # FORZAMOS A ESPERAR 2 SEGUNDOS EXTRA después de que la página se considere cargada
                    'playwright_page_methods': [
                        ('wait_for_timeout', 2000), # Espera 2000 milisegundos (2 segundos)
                    ]
                }
            )

    def start_requests(self):
        for url in self.start_urls:
            # CRÍTICO: Añadir meta={'playwright': True} a la solicitud inicial
            yield scrapy.Request(
                url, 
                headers=self.custom_headers, 
                callback=self.parse,
                 meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        ('wait_for_timeout', 2000), # Espera 2 segundos
                    ]
                }
            )