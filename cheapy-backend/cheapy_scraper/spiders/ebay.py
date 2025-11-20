"""
Spider de eBay para extracción de productos.

Este spider rastrea el marketplace de eBay utilizando Playwright para
renderizado de JavaScript, extrayendo información de productos con
filtrado de contenido para evitar items promocionales genéricos.
"""

import scrapy
from config import EBAY_DOMAINS, COUNTRY_CURRENCIES, ACCEPT_LANGUAGE_BY_COUNTRY
from scrapy_playwright.page import PageMethod


class EbaySpider(scrapy.Spider):
    """
    Spider de Scrapy para la plataforma de comercio electrónico eBay.

    Utiliza Playwright para renderizado de JavaScript para manejar contenido dinámico.
    Extrae listados de productos desde resultados de búsqueda de eBay con filtrado
    para excluir contenido promocional genérico e items patrocinados.
    """

    name = "ebay"

    # Configuración de Playwright para renderizado de JavaScript
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True  # Headless mode for production performance
        }
    }

    def __init__(self, query="", country="US", **kwargs):
        """
        Inicializa el spider con parámetros de búsqueda y configuración de dominio.

        Args:
            query: Término de búsqueda para consulta de productos.
            country: Código de país para selección de dominio de eBay (ej. 'US', 'UK', 'DE').
        """
        super().__init__(**kwargs)
        self.query = query
        self.country_code = country.upper()

        # Obtener dominio y moneda desde configuración centralizada
        domain = EBAY_DOMAINS.get(self.country_code, EBAY_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')

        # Construct search URL for the appropriate eBay domain
        self.start_urls = [f"https://www.ebay.{domain}/sch/i.html?_nkw={self.query.replace(' ', '+')}"]

        self.logger.info(f"Initializing eBay spider for country: {self.country_code}, domain: {domain}")

        # Dynamic Accept-Language header based on country
        self.accept_language = ACCEPT_LANGUAGE_BY_COUNTRY.get(
            self.country_code,
            ACCEPT_LANGUAGE_BY_COUNTRY.get('DEFAULT', 'en-US,en;q=0.9')
        )

    def start_requests(self):
        """
        Generate initial requests with Playwright configuration.

        Configures Playwright to wait for product cards to load,
        ensuring dynamic content is available before parsing.
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers={
                    'Accept-Language': self.accept_language,
                },
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'li.s-card', timeout=30000)
                    ],
                }
            )

    def parse(self, response):
        """
        Parse eBay search results and extract product items.

        Filters out generic promotional content and sponsored items
        by checking for meaningful product titles.

        Args:
            response: Scrapy response object with rendered HTML.
        """
        products = response.css('li.s-card')
        self.logger.info(f"Found {len(products)} products on eBay page.")

        for product in products:
            title = product.css('div.s-card__title span::text').get()

            # Filter out generic promotional content
            if not title or "Shop on eBay" in title:
                continue

            # Extract product data for valid items
            yield {
                'title': title.strip() if title else None,
                'url': product.css('a.image-treatment::attr(href)').get(),
                'image_url': product.css('img.s-card__image::attr(src)').get(),
                'source': self.name,
                'price': product.css('span.s-card__price::text').get(),
                'rating_str': None,  # Not available on search results page
                'reviews_count_str': None,  # Not available on search results page
                'currency_code': self.currency,
                'country_code': self.country_code,
            }