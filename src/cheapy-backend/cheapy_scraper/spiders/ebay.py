"""
Spider de eBay para extracción de productos.

Este spider rastrea el marketplace de eBay utilizando Playwright para
renderizado de JavaScript, extrayendo información de productos con
filtrado de contenido para evitar items promocionales genéricos.
"""

import scrapy
from config import EBAY_DOMAINS, COUNTRY_CURRENCIES
from scrapy_playwright.page import PageMethod
from .base_spider import BaseCheapySpider


class EbaySpider(BaseCheapySpider):
    """
    Spider de Scrapy para la plataforma de comercio electrónico eBay.

    Hereda de BaseCheapySpider para configuración común de headers y país.
    Utiliza Playwright para renderizado de JavaScript y manejo de contenido dinámico.
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
            'headless': True  # Modo headless para rendimiento en producción
        }
    }

    def __init__(self, query="", country="US", **kwargs):
        """
        Inicializa el spider con parámetros de búsqueda y configuración regional.

        Args:
            query: Término de búsqueda para consulta de productos
            country: Código de país para selección de dominio de eBay (ej. 'US', 'UK', 'DE')
        """
        # Inicializar clase base con configuración de país
        super().__init__(country=country, **kwargs)
        self.query = query

        # Obtener dominio y moneda desde configuración centralizada
        domain = EBAY_DOMAINS.get(self.country_code, EBAY_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')

        # Construir URL de búsqueda para el dominio apropiado
        self.start_urls = [f"https://www.ebay.{domain}/sch/i.html?_nkw={self.query.replace(' ', '+')}"]

        self.logger.info(f"Inicializando spider de eBay para país: {self.country_code}, dominio: {domain}")

    def start_requests(self):
        """
        Genera requests iniciales con configuración de Playwright.

        Configura Playwright para esperar a que se carguen las tarjetas de productos,
        asegurando que el contenido dinámico esté disponible antes del parsing.
        """
        headers = self.get_default_headers()

        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers=headers,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'li.s-card', timeout=30000)
                    ],
                }
            )

    def parse(self, response):
        """
        Parsea resultados de búsqueda de eBay y extrae items de productos.

        Filtra contenido promocional genérico y items patrocinados
        verificando títulos de productos significativos.

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