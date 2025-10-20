import scrapy
from config import ALIEXPRESS_DOMAINS, COUNTRY_CURRENCIES
from scrapy_playwright.page import PageMethod

class AliexpressSpider(scrapy.Spider):
    name = "aliexpress"
    custom_settings = {
        'DOWNLOAD_HANDLERS': { "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler", "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler" },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True # <-- CAMBIO 1: Poner en False para ver el navegador
        }
    }

    def __init__(self, query="", country="US", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.country_code = country.upper()
        
        # Obtenemos el host completo desde el config, usando www.aliexpress.com como fallback
        hostname = ALIEXPRESS_DOMAINS.get(self.country_code, ALIEXPRESS_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')
        
        # Construimos la URL correcta
        self.start_urls = [f"https://{hostname}/w/wholesale-{self.query.replace(' ', '-')}.html"]
        
        self.logger.info(f"Iniciando AliExpress spider para País: {self.country_code}, Hostname: {hostname}")
    
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url, 
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        # CAMBIO 2: Añadimos una espera genérica y una pausa
                        PageMethod('wait_for_load_state', 'networkidle', timeout=60000),
                        PageMethod('pause'), # <-- PAUSA PARA INSPECCIONAR
                    ],
                }
            )

    def parse(self, response):
        # NOTA: Los selectores de AliExpress son ofuscados y cambian constantemente. Esto es solo un ejemplo.
        products = response.css('div[class*="product-container"]')
        for product in products:
            yield {
                'title': product.css('h3[class*="product-title"]::text').get(),
                'url': response.urljoin(product.css('a[class*="product-item-inner"]::attr(href)').get() or ''),
                'image_url': product.css('img[class*="product-img"]::attr(src)').get(),
                'source': self.name,
                'price': product.css('div[class*="product-price-value"]::text').get(),
                'rating_str': product.css('span[class*="product-rating-value"]::text').get(),
                'reviews_count_str': product.css('span[class*="product-reviewer"]::text').get(),
                'currency_code': self.currency,
            }