import scrapy
import re

class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"

    def __init__(self, query="", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.start_url = f"https://listado.mercadolibre.com.ar/{self.query.replace(' ', '-')}"
    
    def start_requests(self):
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse,
            errback=self.handle_error
        )

    def parse(self, response):
        self.logger.info(f"MercadoLibreSpider: Parseando {response.url}")

        # Selector "Camaleón" que busca ambos tipos de contenedores
        items = response.css('li.ui-search-layout__item, div.ui-search-result__content')
        
        self.logger.info(f"MercadoLibreSpider: Encontrados {len(items)} items usando selectores combinados.")

        if not items:
            self.logger.warning("MercadoLibreSpider: No se encontró ningún contenedor de producto.")
            return

        item_count = 0
        for item in items[:20]: # Extraemos hasta 20 para tener buen margen para filtrar
            # Lógica de extracción tolerante
            title = item.css('h2.ui-search-item__title::text').get()
            url = item.css('a.ui-search-link::attr(href)').get()
            
            if not title or not url:
                self.logger.debug(f"Item descartado por falta de título o URL. Título: '{title}', URL: '{url}'")
                continue

            # Datos opcionales
            price_fraction = item.css('span.andes-money-amount__fraction::text').get()
            price_symbol = item.css('span.andes-money-amount__currency-symbol::text').get()
            rating_str = item.css('.ui-search-reviews__rating-number::text').get()
            
            price = "Sin precio"
            if price_fraction:
                price = f"{(price_symbol or '$').strip()} {price_fraction.strip().replace('.', '')}"
            
            rating = 0.0
            if rating_str:
                try: rating = float(rating_str.replace(',', '.'))
                except: pass

            item_count += 1
            yield {
                "title": title.strip(),
                "price": price,
                "url": response.urljoin(url),
                "source": "Mercado Libre",
                "reliability_score": round(rating)
            }
        
        self.logger.info(f"MercadoLibreSpider: Se extrajeron {item_count} productos.")

    def handle_error(self, failure):
        self.logger.error(f"FALLO en petición. Razón: {repr(failure)}")