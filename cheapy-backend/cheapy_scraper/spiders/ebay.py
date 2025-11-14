import scrapy
from config import EBAY_DOMAINS, COUNTRY_CURRENCIES
from scrapy_playwright.page import PageMethod

class EbaySpider(scrapy.Spider):
    name = "ebay"
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True  # Poner en True para producción/velocidad
        }
    }

    def __init__(self, query="", country="US", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.country_code = country.upper()
        domain = EBAY_DOMAINS.get(self.country_code, EBAY_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')
        self.start_urls = [f"https://www.ebay.{domain}/sch/i.html?_nkw={self.query.replace(' ', '+')}"]
        self.logger.info(f"Iniciando eBay spider para País: {self.country_code}, Dominio: {domain}")

    def start_requests(self):
        for url in self.start_urls:
            # Esperamos a que aparezca el nuevo contenedor 'li.s-card'
            yield scrapy.Request(
                url, 
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'li.s-card', timeout=30000)
                    ],
                }
            )

    def parse(self, response):
        # Usamos el nuevo selector para el contenedor de productos
        products = response.css('li.s-card')
        self.logger.info(f"Se encontraron {len(products)} productos en la página de eBay.")
        
        for product in products:
            title = product.css('div.s-card__title span::text').get()
            
             # --- ¡AQUÍ ESTÁ EL FILTRO! ---
            # Si no hay título, o si el título es el genérico,
            # saltamos esta iteración y pasamos al siguiente 'product'.
            if not title or "Shop on eBay" in title:
                continue
            # Si el código llega hasta aquí, es un producto real.
            # Procedemos a extraer el resto de los datos.
            yield {
                'title': title.strip() if title else None,
                'url': product.css('a.image-treatment::attr(href)').get(),
                'image_url': product.css('img.s-card__image::attr(src)').get(),
                'source': self.name,
                'price': product.css('span.s-card__price::text').get(),
                'rating_str': None, # No disponible en la página de búsqueda
                'reviews_count_str': None, # No disponible en la página de búsqueda
                'currency_code': self.currency,
                'country_code': self.country_code,
            }