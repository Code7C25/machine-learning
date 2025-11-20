"""
Spider de AliExpress para extracción de productos.

Este spider rastrea el marketplace de AliExpress utilizando Playwright para
renderizado de JavaScript, extrayendo información de productos con
carga de contenido dinámico y manejo de paginación.
"""

import scrapy
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from cheapy_scraper.items import ProductItem
from config import COUNTRY_CURRENCIES, ACCEPT_LANGUAGE_BY_COUNTRY
from scrapy_playwright.page import PageMethod


class AliexpressSpider(scrapy.Spider):
    """
    Spider de Scrapy para la plataforma de comercio electrónico AliExpress.

    Utiliza Playwright para renderizado de JavaScript para manejar contenido dinámico.
    Extrae listados de productos con precios, calificaciones y reseñas desde
    resultados de búsqueda de AliExpress en múltiples países.
    """

    name = "aliexpress"
    MAX_PAGES = 2

    # Configuración de Playwright para renderizado de JavaScript
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler"
        },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': False  # Visible browser for debugging
        }
    }

    def __init__(self, query="", country="AR", **kwargs):
        """
        Inicializa el spider con parámetros de búsqueda y configuración del navegador.

        Args:
            query: Término de búsqueda para consulta de productos (requerido).
            country: Código de país para búsqueda localizada y moneda.

        Raises:
            ValueError: Si no se proporciona el parámetro query.
        """
        super().__init__(**kwargs)
        if not query:
            raise ValueError("Query parameter is required.")

        self.query = query
        self.country_code = country.upper()

        # AliExpress primarily uses USD, but attempt country-specific currency
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')

        # Dynamic Accept-Language header based on country
        accept_language = ACCEPT_LANGUAGE_BY_COUNTRY.get(
            self.country_code,
            ACCEPT_LANGUAGE_BY_COUNTRY.get('DEFAULT', 'en-US,en;q=0.9')
        )

        # Browser headers to mimic real user requests
        self.custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': accept_language,
            'Referer': 'https://www.google.com/',
        }

        # Construct initial search URL with query parameters
        base_url = "https://www.aliexpress.com/wholesale"
        params = {
            'SearchText': self.query,
            'page': 1,
            'g': 'y'  # Parameter sometimes required for result loading
        }

        self.start_urls = [f"{base_url}?{urlencode(params)}"]
        self.current_page = 1

        self.logger.info(f"Initializing AliExpress spider for query: {self.query}")

    def normalize_url(self, url):
        """
        Normalize AliExpress URLs by removing tracking parameters.

        AliExpress URLs contain extensive tracking parameters. This method
        strips query strings and fragments to get clean product URLs.

        Args:
            url: Raw URL from AliExpress.

        Returns:
            str: Normalized URL with tracking parameters removed.
        """
        if not url:
            return url

        parsed = urlparse(url)
        # For AliExpress, the product identifier is typically in the path
        # Example: /item/100500123456.html
        return urlunparse(parsed._replace(query='', fragment=''))

    def parse(self, response):
        """
        Parse search results page and extract product items.

        Handles AliExpress's dynamic HTML structure rendered by Playwright,
        extracting product details and implementing pagination.

        Args:
            response: Scrapy response object with rendered HTML.
        """
        self.logger.info(f"Parsing page {self.current_page}/{self.MAX_PAGES} - {response.url}")

        # Extract product containers with fallback selectors
        item_containers = response.css('div[data-spm="product_list"]')
        if not item_containers:
            item_containers = response.css('div.man-pc-search-item-card')

        # Debug: Save HTML if no items found
        if not item_containers:
            filename = f'aliexpress_debug_page_{self.current_page}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            self.logger.critical(
                f"DEBUG: No items found. HTML saved to {filename} for inspection."
            )

        for item in item_containers:
            # Extract product URL and title
            link = (
                item.css('a.man-pc-search-item-card__title::attr(href)').get() or
                item.css('a::attr(href)').get()
            )

            if link and not link.startswith('http'):
                link = response.urljoin(link)

            title = (
                item.css('a.man-pc-search-item-card__title::text').get() or
                item.css('div.man-pc-search-item-card__title::text').get()
            )

            # Extract current price
            price_current = (
                item.css('div.man-pc-search-item-card__price-current::text').get() or
                item.css('.price-current::text').get()
            )

            # Extract product image
            image_url = item.css('img.man-pc-search-item-card__thumbnail-img::attr(src)').get()

            # Extract rating and review information
            rating_str = item.css('.man-pc-search-item-card__star-level::text').get()
            reviews_count_str = item.css('.man-pc-search-item-card__feedback::text').get()

            # Skip incomplete items
            if not title or not link or not price_current:
                self.logger.debug(
                    f"Skipping incomplete item. Title: {title}, Link: {link}, Price: {price_current}"
                )
                continue

            # Create and normalize product item
            normalized_url = self.normalize_url(link)

            product = ProductItem()
            product['title'] = title.strip() if title else None
            product['url'] = normalized_url
            product['image_url'] = image_url
            product['source'] = self.name
            product['price'] = price_current.strip()
            product['rating_str'] = rating_str
            product['reviews_count_str'] = reviews_count_str
            product['currency_code'] = self.currency
            product['country_code'] = self.country_code

            yield product

        # Pagination logic using page parameter
        if self.current_page < self.MAX_PAGES:
            self.current_page += 1

            # Parse current URL and update page parameter
            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)

            query_params['page'] = [str(self.current_page)]

            new_query = urlencode(query_params, doseq=True)
            next_page_url = urlunparse(parsed_url._replace(query=new_query, fragment=''))

            self.logger.info(f"Calculated next AliExpress URL (Page {self.current_page})")

            yield scrapy.Request(
                url=next_page_url,
                headers=self.custom_headers,
                callback=self.parse,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_timeout', 2000),  # Wait 2 seconds for content load
                    ]
                }
            )

    def start_requests(self):
        """
        Generate initial requests with Playwright configuration.

        Ensures all requests use Playwright for JavaScript rendering
        with appropriate wait times for dynamic content loading.
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers=self.custom_headers,
                callback=self.parse,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_timeout', 2000),  # Initial 2-second wait
                    ]
                }
            )