import scrapy
from config import AMAZON_DOMAINS, COUNTRY_CURRENCIES
from scrapy_playwright.page import PageMethod

class AmazonSpider(scrapy.Spider):
    name = "amazon"
    custom_settings = {
        'DOWNLOAD_HANDLERS': { "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler", "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler" },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True  # <-- CAMBIO 1: Poner en False para ver el navegador
        }
    }

    def __init__(self, query="", country="US", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.country_code = country.upper()
        domain = AMAZON_DOMAINS.get(self.country_code, AMAZON_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')
        self.start_urls = [f"https://www.amazon.{domain}/s?k={self.query.replace(' ', '+')}"]
        self.logger.info(f"Iniciando Amazon spider para País: {self.country_code}, Dominio: {domain}")

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url, 
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'div[data-component-type="s-search-result"]', timeout=45000),
                        # PageMethod('pause'),
                        ],
                    },
                errback=self.errback_close_page,
                )
    
    async def errback_close_page(self, failure):
        """
        Callback de error para cerrar la página de Playwright si algo falla.
        """
        page = failure.request.meta["playwright_page"]
        await page.close()
        self.logger.error(f"Error en Playwright al cargar la página: {failure.value}")


    def parse(self, response):
        # Selector principal para cualquier tipo de tarjeta de resultado
        products = response.css('div[data-component-type="s-search-result"]')
        
        for product in products:
            # --- Selectores Flexibles ---

            # Título: Prueba el selector que encontramos, y también uno más genérico
            title = product.css(
                'div.s-title-instructions-style a h2 span::text, '  # El que encontramos
                'h2 a span::text'                                  # Uno más simple como fallback
            ).get()

            # URL: Prueba varias clases comunes para el enlace del producto
            product_url = product.css(
                'a.s-no-outline::attr(href), '
                'div.s-title-instructions-style a::attr(href), '
                'h2 a::attr(href)'
            ).get()

            # Precio: Lógica multi-formato
            price_full_str = None
            price_whole = product.css('span.a-price-whole::text').get()
            price_fraction = product.css('span.a-price-fraction::text').get()
            if price_whole and price_fraction:
                price_full_str = f"{price_whole.replace(',', '')}.{price_fraction}"
            else:
                price_full_str = product.css('div.a-color-secondary span.a-color-base::text').get()

            # Rating y Reseñas:
            rating_str = product.css('span.a-icon-alt::text').get() # Este suele ser muy consistente
            reviews_count_str = product.css(
                'span.a-size-base.s-underline-text::text, '
                'div.a-row.a-size-small a span[aria-hidden="true"]::text'
            ).get()

            yield {
                'title': title,
                'url': response.urljoin(product_url) if product_url and 'javascript' not in product_url else None,
                'image_url': product.css('img.s-image::attr(src)').get(),
                'source': self.name,
                'price': price_full_str,
                'rating_str': rating_str.split(' ')[0] if rating_str else None,
                'reviews_count_str': reviews_count_str,
                'currency_code': self.currency,
                'country_code': self.country_code
            }