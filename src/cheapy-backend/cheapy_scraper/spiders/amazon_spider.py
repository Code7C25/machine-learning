"""
Spider de Amazon para extracción de productos.

Este spider rastrea el marketplace de Amazon utilizando Playwright para
renderizado de JavaScript, extrayendo información de productos a través
de múltiples dominios de Amazon con resultados de búsqueda localizados.
"""

import scrapy
from config import AMAZON_DOMAINS, COUNTRY_CURRENCIES
from scrapy_playwright.page import PageMethod
from .base_spider import BaseCheapySpider


class AmazonSpider(BaseCheapySpider):
    """
    Spider de Scrapy para la plataforma de comercio electrónico Amazon.

    Hereda de BaseCheapySpider para configuración común de headers y país.
    Utiliza Playwright para renderizado de JavaScript y manejo de contenido dinámico.
    """

    name = "amazon"

    # Configuración de Playwright para renderizado de JavaScript
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler"
        },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True  # Modo headless para producción
        }
    }

    def __init__(self, query="", country="US", **kwargs):
        """
        Inicializa el spider con parámetros de búsqueda y configuración regional.

        Args:
            query: Término de búsqueda para consulta de productos
            country: Código de país para selección de dominio de Amazon (ej. 'US', 'BR', 'MX')
        """
        # Inicializar clase base con configuración de país
        super().__init__(country=country, **kwargs)
        self.query = query

        # Obtener dominio y moneda desde configuración centralizada
        domain = AMAZON_DOMAINS.get(self.country_code, AMAZON_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')

        # Construir URL de búsqueda para el dominio apropiado
        self.start_urls = [f"https://www.amazon.{domain}/s?k={self.query.replace(' ', '+')}"]

        self.logger.info(f"Inicializando spider de Amazon para país: {self.country_code}, dominio: {domain}")

    def start_requests(self):
        """
        Genera requests iniciales con configuración de Playwright.

        Configura Playwright para esperar a que se carguen los resultados de búsqueda
        antes del parsing, asegurando que el contenido dinámico esté disponible.
        """
        headers = self.get_default_headers()

        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers=headers,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'div[data-component-type="s-search-result"]', timeout=45000),
                    ],
                },
                errback=self.errback_close_page,
            )

    async def errback_close_page(self, failure):
        """
        Callback de error para cerrar correctamente la página de Playwright.

        Asegura que las páginas del navegador de Playwright se limpien cuando
        las requests fallan, previniendo fugas de recursos en entornos de producción.

        Args:
            failure: Objeto de fallo de Scrapy con detalles del error
        """
        page = failure.request.meta["playwright_page"]
        await page.close()
        self.logger.error(f"Error de carga de página Playwright: {failure.value}")

    def parse(self, response):
        """
        Parse Amazon search results and extract product items.

        Handles Amazon's complex HTML structure with multiple fallback
        selectors for robust data extraction across different layouts.

        Args:
            response: Scrapy response object with rendered HTML.
        """
        # Extract product containers using Amazon's data attributes
        products = response.css('div[data-component-type="s-search-result"]')

        for product in products:
            # Extract product title with multiple fallback selectors
            title = product.css(
                'div.s-title-instructions-style a h2 span::text, '
                'h2 a span::text'
            ).get()

            # Extract product URL with multiple link selectors
            product_url = product.css(
                'a.s-no-outline::attr(href), '
                'div.s-title-instructions-style a::attr(href), '
                'h2 a::attr(href)'
            ).get()

            # Extract price with handling for different Amazon price formats
            price_full_str = None
            price_whole = product.css('span.a-price-whole::text').get()
            price_fraction = product.css('span.a-price-fraction::text').get()

            if price_whole and price_fraction:
                # Construct decimal price from whole and fraction parts
                price_full_str = f"{price_whole.replace(',', '')}.{price_fraction}"
            else:
                # Fallback for alternative price formats
                price_full_str = product.css('div.a-color-secondary span.a-color-base::text').get()

            # Extract rating and review information
            rating_str = product.css('span.a-icon-alt::text').get()
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