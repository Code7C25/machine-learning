import scrapy
from config import COUNTRY_CURRENCIES

class FravegaSpider(scrapy.Spider):
    name = "fravega"

    # No se necesita Playwright.
    
    def __init__(self, query="", country="AR", **kwargs):
        super().__init__(**kwargs)
        if country.upper() != 'AR':
            self.logger.warning(f"El spider de Fravega solo soporta 'AR'. Se ignora el país '{country}'.")
        
        self.query = query
        self.country_code = "AR"
        self.currency = COUNTRY_CURRENCIES.get(self.country_code)
        self.start_urls = [f"https://www.fravega.com/l/?keyword={self.query.replace(' ', '%20')}"]
        self.logger.info(f"Iniciando Fravega spider para query: '{self.query}'")

    def parse(self, response):
        # Selector para el contenedor principal de cada producto
        products = response.css('article[data-test-id="result-item"]')
        self.logger.info(f"Se encontraron {len(products)} productos en la página de Fravega.")
        
        for product in products:
            # La URL es el 'href' del primer enlace 'a' que se encuentra dentro del artículo
            url = product.css('a::attr(href)').get()
            
            yield {
                # Selector para el título
                'title': product.css('div[data-test-id="article-title"] span::text').get(),
                'url': response.urljoin(url or ''),
                
                # Selector para la imagen (buscamos la img dentro de la etiqueta picture)
                'image_url': product.css('picture img::attr(src)').get(),
                
                'source': self.name,
                
                # Selector para el precio
                'price': product.css('div[data-test-id="product-price"] span::text').get(),

                'rating_str': None,
                'reviews_count_str': None,
                'currency_code': self.currency,
                'country_code': self.country_code,
            }