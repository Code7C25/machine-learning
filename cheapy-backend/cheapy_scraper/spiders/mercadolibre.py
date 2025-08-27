import scrapy
import re

class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"

    def __init__(self, query="", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.start_url = f"https://listado.mercadolibre.com.ar/{self.query.replace(' ', '-')}"
    
    def start_requests(self):
        yield scrapy.Request(url=self.start_url, callback=self.parse, errback=self.handle_error)

    def parse(self, response):
        self.logger.info(f"MercadoLibreSpider: Parseando {response.url}")
        
        items = response.css('li.ui-search-layout__item, div.poly-card--list')
        self.logger.info(f"MercadoLibreSpider: Encontrados {len(items)} contenedores de items.")
        
        item_count = 0
        for item in items[:40]:
            title = item.css('h2.ui-search-item__title::text').get() or \
                    item.css('h3.poly-component__title-wrapper a.poly-component__title::text').get()

            url = item.css('a.ui-search-link::attr(href)').get() or \
                  item.css('a.poly-component__title::attr(href)').get()

            if not title or not url:
                continue

            price_fraction = item.css('span.andes-money-amount__fraction::text').get()
            price_symbol = item.css('span.andes-money-amount__currency-symbol::text').get()
            
            # --- LÓGICA DE RATING Y RESEÑAS MEJORADA ---
            rating_str = item.css('.ui-search-reviews__rating-number::text').get() or \
                         item.css('span.poly-reviews__rating::text').get()
            
            # Buscamos el total de reseñas en ambos layouts
            reviews_count_str = item.css('.ui-search-reviews__amount::text').get() or \
                                item.css('span.poly-reviews__total::text').get()

            # --- Procesamiento de Datos ---
            price = "Sin precio"
            if price_fraction:
                price = f"{(price_symbol or '$').strip()} {price_fraction.strip().replace('.', '')}"
            
            rating = 5.0
            if rating_str:
                try: rating = float(rating_str.replace(',', '.'))
                except: rating = 0.0

            reviews_count = 0
            if reviews_count_str:
                # Extraemos solo los números de "(680)"
                numbers = re.findall(r'\d+', reviews_count_str)
                if numbers:
                    reviews_count = int(numbers[0])
            
            item_count += 1
            yield {
                "title": title.strip(),
                "price": price,
                "url": response.urljoin(url),
                "source": "Mercado Libre",
                "reliability_score": round(rating),
                # --- NUEVO CAMPO AÑADIDO ---
                "reviews_count": reviews_count
            }
        
        self.logger.info(f"MercadoLibreSpider: Se extrajeron {item_count} productos.")

    def handle_error(self, failure):
        self.logger.error(f"FALLO en la petición: {repr(failure)}")