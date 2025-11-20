"""
Spider de Amazon para extracción de productos.

Este spider rastrea el marketplace de Amazon utilizando Playwright para
renderizado de JavaScript, extrayendo información de productos a través
de múltiples dominios de Amazon con resultados de búsqueda localizados.
"""

import scrapy
from config import AMAZON_DOMAINS, COUNTRY_CURRENCIES, ACCEPT_LANGUAGE_BY_COUNTRY
from scrapy_playwright.page import PageMethod


class AmazonSpider(scrapy.Spider):
    """
    Spider de Scrapy para la plataforma de comercio electrónico Amazon.

    Utiliza Playwright para renderizado de JavaScript para manejar contenido dinámico
    y medidas anti-bot. Extrae listados de productos desde resultados de búsqueda
    de Amazon a través de múltiples dominios de países con precios localizados.
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
            'headless': True  # Headless mode for production
        }
    }

    def __init__(self, query="", country="US", **kwargs):
        """
        Inicializa el spider con parámetros de búsqueda y configuración de dominio.

        Args:
            query: Término de búsqueda para consulta de productos.
            country: Código de país para selección de dominio de Amazon (ej. 'US', 'BR', 'MX').
        """
        super().__init__(**kwargs)
        self.query = query
        self.country_code = country.upper()

        # Obtener dominio y moneda desde configuración centralizada
        domain = AMAZON_DOMAINS.get(self.country_code, AMAZON_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')

        # Construct search URL for the appropriate Amazon domain
        self.start_urls = [f"https://www.amazon.{domain}/s?k={self.query.replace(' ', '+')}"]

        self.logger.info(f"Initializing Amazon spider for country: {self.country_code}, domain: {domain}")

        # Dynamic Accept-Language header based on country
        self.accept_language = ACCEPT_LANGUAGE_BY_COUNTRY.get(
            self.country_code,
            ACCEPT_LANGUAGE_BY_COUNTRY.get('DEFAULT', 'en-US,en;q=0.9')
        )

    def start_requests(self):
        """
        Generate initial requests with Playwright configuration.

        Configures Playwright to wait for search results to load
        before parsing, ensuring dynamic content is available.
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
                        PageMethod('wait_for_selector', 'div[data-component-type="s-search-result"]', timeout=45000),
                    ],
                },
                errback=self.errback_close_page,
            )

    async def errback_close_page(self, failure):
        """
        Error callback to properly close Playwright page on failure.

        Ensures Playwright browser pages are cleaned up when requests fail,
        preventing resource leaks in production environments.

        Args:
            failure: Scrapy failure object containing error details.
        """
        page = failure.request.meta["playwright_page"]
        await page.close()
        self.logger.error(f"Playwright page load error: {failure.value}")

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