# cheapy-backend/cheapy_scraper/spiders/mercadolibre.py

import scrapy

class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"
    MAX_PAGES = 4

    # (El resto de tu configuración inicial como custom_headers y __init__ permanece igual)
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
        # ... resto de tus headers ...
    }

    def __init__(self, query="", **kwargs):
        super().__init__(**kwargs)
        if not query:
            raise ValueError("El argumento 'query' es obligatorio.")
        self.query = query
        base_url = f"https://listado.mercadolibre.com.ar/{self.query.replace(' ', '-')}"
        self.start_urls = [base_url]
        self.page_count = 0

    def parse(self, response):
        self.page_count += 1
        self.logger.info(f"Parseando página {self.page_count}/{self.MAX_PAGES} - {response.url}")

        for item in response.css('li.ui-search-layout__item'):
            # Combinamos selectores con una coma. Scrapy encontrará el primero que exista.
            # Usamos .get() que devuelve el primero, o .getall() si esperamos múltiples.
            
            title = item.css('a.poly-component__title::text, h2.ui-search-item__title::text').get()
            
            url = item.css('a.poly-component__title::attr(href), a.ui-search-link::attr(href)').get()

            # Para imágenes, buscamos todas las posibles combinaciones de clases y atributos
            image_url = item.css('.ui-search-result__image-container img::attr(data-src)').get() or \
            item.css('.ui-search-result__image-container img::attr(src)').get() or \
            item.css('.poly-card__portada img::attr(data-src)').get() or \
            item.css('.poly-card__portada img::attr(src)').get()

            rating_str = item.css('span.poly-reviews__rating::text, .ui-search-reviews__rating-number::text').get()

            reviews_count_str = item.css('span.poly-reviews__total::text, .ui-search-reviews__amount::text').get()
            
            # El precio es el más consistente, pero lo protegemos de igual manera.
            # Es importante buscar DENTRO del item actual.
            price_symbol = item.css('.andes-money-amount__currency-symbol::text').get()
            price_fraction = item.css('.andes-money-amount__fraction::text').get()
            
            # En productos con descuento, hay DOS fracciones de precio. Debemos asegurarnos de tomar la correcta.
            # La correcta está dentro del div.poly-price__current o directamente en ui-search-price.
            price_fraction_discount = item.css('div.poly-price__current .andes-money-amount__fraction::text').get()
            price_fraction_normal = item.css('.ui-search-price .andes-money-amount__fraction::text').get()

            # Si hay un precio con descuento, lo usamos. Si no, usamos el normal. Si no, el genérico.
            final_price_fraction = price_fraction_discount or price_fraction_normal or price_fraction

            price_full_str = f"{price_symbol or ''}{final_price_fraction or ''}"

            yield {
                'title': title,
                'url': url,
                'image_url': image_url,
                'source': self.name,
                'price': price_full_str if final_price_fraction else None,
                'rating_str': rating_str,
                'reviews_count_str': reviews_count_str,
            }

        # La lógica de paginación no cambia y está perfecta
        if self.page_count < self.MAX_PAGES:
            next_page_url = response.css('li.andes-pagination__button--next a.andes-pagination__link::attr(href)').get()
            if next_page_url:
                yield scrapy.Request(url=next_page_url, callback=self.parse)

    def start_requests(self):
        # Es una buena práctica usar start_requests para pasar headers
        for url in self.start_urls:
            yield scrapy.Request(url, headers=self.custom_headers, callback=self.parse)