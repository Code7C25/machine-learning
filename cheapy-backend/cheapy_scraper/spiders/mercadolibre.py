# cheapy-backend/cheapy_scraper/spiders/mercadolibre.py

import scrapy
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode 
from cheapy_scraper.items import ProductItem
# Se importan las configuraciones centralizadas
from config import MERCADOLIBRE_DOMAINS, COUNTRY_CURRENCIES

class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"
    MAX_PAGES = 2
    ITEMS_PER_PAGE = 48 # Número típico de ítems por página en MercadoLibre
    
    # El diccionario 'meli_domains' se ha movido a config.py
    
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
        # ... resto de tus headers ...
    }

    def __init__(self, query="", country="AR", **kwargs):
        super().__init__(**kwargs)
        if not query:
            raise ValueError("El argumento 'query' es obligatorio.")
        
        self.query = query
        self.country_code = country.upper()
        
        # Se usan las variables importadas desde config.py
        domain = MERCADOLIBRE_DOMAINS.get(self.country_code, MERCADOLIBRE_DOMAINS['AR'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD') # Usamos USD como fallback genérico
        
        base_url = f"https://listado.mercadolibre.{domain}/{self.query.replace(' ', '-')}"
        self.start_urls = [base_url]
        self.page_count = 0
        
        self.logger.info(f"Iniciando spider para País: {self.country_code}, Dominio: {domain}, Moneda: {self.currency}")

    def parse(self, response):
        self.page_count += 1
        self.logger.info(f"Parseando página {self.page_count}/{self.MAX_PAGES} - {response.url}")

        for item in response.css('li.ui-search-layout__item'):
            title = item.css('a.poly-component__title::text, h2.ui-search-item__title::text').get()
            url = item.css('a.poly-component__title::attr(href), a.ui-search-link::attr(href)').get()

            # Selector de imagen EXACTAMENTE como lo tenías
            image_url = item.css('.ui-search-result__image-container img::attr(data-src)').get() or \
            item.css('.ui-search-result__image-container img::attr(src)').get() or \
            item.css('.poly-card__portada img::attr(data-src)').get() or \
            item.css('.poly-card__portada img::attr(src)').get()

            rating_str = item.css('span.poly-reviews__rating::text, .ui-search-reviews__rating-number::text').get()
            reviews_count_str = item.css('span.poly-reviews__total::text, .ui-search-reviews__amount::text').get()
            
            price_symbol = item.css('.andes-money-amount__currency-symbol::text').get()
            price_fraction = item.css('.andes-money-amount__fraction::text').get()
            price_fraction_discount = item.css('div.poly-price__current .andes-money-amount__fraction::text').get()
            price_fraction_normal = item.css('.ui-search-price .andes-money-amount__fraction::text').get()
            final_price_fraction = price_fraction_discount or price_fraction_normal or price_fraction
            price_full_str = f"{price_symbol or ''}{final_price_fraction or ''}"

            product = ProductItem()
            product['title'] = title
            product['url'] = url
            product['image_url'] = image_url
            product['source'] = self.name
            product['price'] = price_full_str if final_price_fraction else None
            product['rating_str'] = rating_str
            product['reviews_count_str'] = reviews_count_str
            product['currency_code'] = self.currency
            product['country_code'] = self.country_code
            yield product

         # --- Lógica de Paginación MODIFICADA (Basada en Offset) ---
        if self.page_count < self.MAX_PAGES:
            
            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            
            # 1. Determinar el desplazamiento actual
            # ML usa _Desde. Si no está, asumimos que estamos en el inicio (offset 0).
            # parse_qs devuelve listas, por eso usamos [0]
            current_offset_str = query_params.get('_Desde', ['0'])[0]
            
            try:
                current_offset = int(current_offset_str)
            except ValueError:
                # Si el valor no es un número (ej: está vacío), empezamos desde 0
                current_offset = 0 
                
            # 2. Calcular el nuevo desplazamiento
            new_offset = current_offset + self.ITEMS_PER_PAGE
            
            # 3. Reemplazar o añadir el nuevo parámetro _Desde
            query_params['_Desde'] = [str(new_offset)]

            # 4. Reconstruir la URL
            # urlencode convierte el diccionario de parámetros de nuevo en una cadena de consulta
            new_query = urlencode(query_params, doseq=True)
            
            # urlunparse reconstruye la URL con la nueva cadena de consulta
            next_page_url = urlunparse(parsed_url._replace(query=new_query, fragment=''))
            
            self.logger.info(f"Calculado: Próxima URL de búsqueda con offset: {new_offset}")

            # 5. Yield la nueva solicitud
            yield scrapy.Request(
                url=next_page_url, 
                headers=self.custom_headers, # ¡Asegúrate de pasar los headers aquí!
                callback=self.parse
            )

    def start_requests(self):
        for url in self.start_urls:
            # Aseguramos que la primera solicitud también use los headers
            yield scrapy.Request(url, headers=self.custom_headers, callback=self.parse)