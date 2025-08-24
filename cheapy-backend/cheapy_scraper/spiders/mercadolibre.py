import scrapy

class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"

    def __init__(self, query="", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.start_url = f"https://listado.mercadolibre.com.ar/{self.query.replace(' ', '-')}"
    
    async def start(self):
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse,
            errback=self.handle_error
        )

    def parse(self, response):
        self.logger.info(f"Parseando URL: {response.url}")
        
        # Un selector que busca AMBOS tipos de contenedores de productos
        items = response.css('li.ui-search-layout__item, div.ui-search-result__content')
        self.logger.info(f"Encontrados {len(items)} contenedores de items.")
        
        item_count = 0
        for item in items:
            # Para cada item, probamos AMBOS selectores de título
            title = item.css('h2.ui-search-item__title::text').get() or \
                    item.css('h3.poly-component__title-wrapper a.poly-component__title::text').get()
            
            # El precio y la URL suelen ser más estables
            price_fraction = item.css('span.andes-money-amount__fraction::text').get()
            price_symbol = item.css('span.andes-money-amount__currency-symbol::text').get()
            url = item.css('a::attr(href)').get()

            if title and price_fraction and url:
                item_count += 1
                yield {
                    "title": title.strip(),
                    "price": f"{(price_symbol or '$').strip()} {price_fraction.strip().replace('.', '')}",
                    "url": response.urljoin(url), # Usamos urljoin para asegurar URL completa
                    "source": "Mercado Libre"
                }
        
        self.logger.info(f"Se extrajeron {item_count} productos.")

    def handle_error(self, failure):
        self.logger.error(f"FALLO en la petición: {repr(failure)}")