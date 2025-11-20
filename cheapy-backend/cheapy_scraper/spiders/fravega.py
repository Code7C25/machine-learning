"""
Spider de Frávega para extracción de productos.

Este spider rastrea la plataforma de comercio electrónico de Frávega en Argentina,
extrayendo información de productos con parsing robusto de precios y
extracción de calificaciones desde su estructura HTML específica.
"""

import re
import scrapy
from config import COUNTRY_CURRENCIES


class FravegaSpider(scrapy.Spider):
    """
    Spider de Scrapy para la plataforma de comercio electrónico Frávega.

    Especializado para extraer listados de productos desde el marketplace argentino
    de Frávega. Maneja estructuras complejas de precios con detección de precios
    actuales/anteriores, extracción de calificaciones y paginación.
    """

    name = "fravega"
    MAX_PAGES = 2

    def __init__(self, query="", country="AR", **kwargs):
        """
        Inicializa el spider con parámetros de búsqueda.

        Args:
            query: Término de búsqueda para consulta de productos.
            country: Código de país (solo 'AR' soportado para Frávega).

        Nota:
            Frávega opera exclusivamente en Argentina, por lo que el parámetro
            country se valida y por defecto es 'AR'.
        """
        super().__init__(**kwargs)
        if country.upper() != 'AR':
            self.logger.warning(
                f"Frávega spider only supports 'AR' country. "
                f"Ignoring provided country '{country}'."
            )

        self.query = query
        self.country_code = "AR"
        self.currency = COUNTRY_CURRENCIES.get(self.country_code)
        self.start_urls = [f"https://www.fravega.com/l/?keyword={self.query.replace(' ', '%20')}"]
        self.page_count = 0

        self.logger.info(f"Initializing Frávega spider for query: '{self.query}'")

    def parse(self, response):
        """
        Parse search results page and extract product items.

        Handles Frávega's product listing structure, extracting detailed
        product information including prices, ratings, and implementing
        pagination logic.

        Args:
            response: Scrapy response object for the current page.
        """
        self.page_count += 1
        self.logger.info(f"Parsing page {self.page_count}/{self.MAX_PAGES} - {response.url}")

        products = response.css('article[data-test-id="result-item"]')
        self.logger.info(f"Found {len(products)} products on Frávega page.")

        for product in products:
            # Extract basic product URL
            url = product.css('a::attr(href)').get()

            # Robust rating and review extraction with multiple fallback selectors
            rating_str = None
            reviews_count_str = None

            # Primary selectors using data attributes
            rating_str = product.css('[data-test-id="product-rating"] ::text').get()
            reviews_count_str = product.css('[data-test-id="product-reviews"] ::text').get()

            # Fallback: Extract from aria-label attributes
            if not rating_str:
                aria = product.css('[aria-label]::attr(aria-label)').get()
                if aria:
                    m = re.search(r"([0-9]+[\.,]?[0-9]*)", aria)
                    if m:
                        rating_str = m.group(1)

            # Fallback: Generic rating selectors
            if not rating_str:
                rating_str = product.css('.rating::text, .product-rating::text, .stars::text').get()

            # Extract review counts from various text patterns
            if not reviews_count_str:
                reviews_count_str = product.css(
                    'span.reviews::text, .review-count::text, .product-review-count::text'
                ).get()

            # Last resort: Search all text for review-related keywords
            if not reviews_count_str:
                possible = product.css('::text').getall()
                if possible:
                    for t in possible:
                        if t and re.search(r"(opinione|opinion|reseñ|review|vendid|vendidos|ventas)", t, re.I):
                            reviews_count_str = t.strip()
                            break

            # Clean extracted strings
            if rating_str:
                rating_str = rating_str.strip()
            if reviews_count_str:
                reviews_count_str = reviews_count_str.strip()

            # Debug logging for successful extractions
            if rating_str or reviews_count_str:
                self.logger.debug(
                    f"Frávega: extracted rating='{rating_str}' "
                    f"reviews='{reviews_count_str}' url={url}"
                )

            # Advanced price extraction with current/previous price detection
            price_container = product.css('div[data-test-id="product-price"]')

            # Collect all monetary text patterns from price container
            price_texts = price_container.css('::text').getall()
            money_candidates = []

            # Build monetary candidates with context
            for idx, t in enumerate(price_texts):
                if not t or not t.strip():
                    continue

                matches = re.findall(r'[\$€£]\s*[\d\.,]+', t)
                if not matches:
                    continue

                # Expand context to include neighboring text
                start = max(0, idx-1)
                end = min(len(price_texts), idx+2)
                ctx = ' '.join([x.strip() for x in price_texts[start:end] if x and x.strip()])

                for match in matches:
                    txt = match.strip()
                    if txt not in [c[0] for c in money_candidates]:
                        money_candidates.append((txt, ctx))

            price_current_text = None
            price_before = None

            # Priority: Extract explicit offer price if available
            try:
                offer_span = price_container.css('span.sc-1d9b1d9e-0::text').get()
            except Exception:
                offer_span = None

            if offer_span and re.search(r'[\$€£]\s*[\d\.,]+', offer_span):
                price_current_text = offer_span.strip()
            else:
                # Extract from direct spans, avoiding tax-related labels
                spans = price_container.css('span::text').getall()
                for s in spans:
                    if not s or not s.strip():
                        continue
                    if (re.search(r'[\$€£]\s*[\d\.,]+', s) and
                        not re.search(r's/?imp|sin\s*imp|precio\s*s/?imp', s, re.I)):
                        price_current_text = s.strip()
                        break

            # Convert monetary strings to numeric values
            def money_to_float(s):
                """
                Convert Frávega's price strings to float values.

                Handles various Argentine number formats including
                European-style decimal separators.

                Args:
                    s: Price string (e.g., "$ 1.234.567,89")

                Returns:
                    float or None: Parsed numeric value
                """
                if not s:
                    return None
                s = re.sub(r'[^\d.,]', '', s)

                # Handle different separator patterns
                if ',' in s and '.' in s:
                    # European format: 1.234,56 (thousands.decimal)
                    s = s.replace('.', '').replace(',', '.')
                elif '.' in s and ',' not in s:
                    # Dots only: could be thousands (1.234.567) or decimal (1.5)
                    parts = s.split('.')
                    if len(parts[-1]) == 3 and len(parts) > 1:
                        # Thousands format: 1.234.567
                        s = ''.join(parts)
                elif ',' in s and '.' not in s:
                    # Commas only: could be thousands (1,234) or decimal (1,5)
                    parts = s.split(',')
                    if len(parts[-1]) == 3 and len(parts) > 1:
                        # Thousands format: 1,234,567
                        s = ''.join(parts)
                    else:
                        # Decimal format: 1,5
                        s = s.replace(',', '.')

                try:
                    return float(s)
                except Exception:
                    return None

            # Map all monetary candidates to numeric values
            money_nums = []
            for txt, ctx in money_candidates:
                v = money_to_float(txt)
                if v is not None:
                    money_nums.append((txt, v, ctx))

            # Determine current price
            price_current = price_current_text
            price_current_numeric = None
            if price_current:
                price_current_numeric = money_to_float(price_current)

            # Fallback: Infer current price from monetary candidates
            if price_current_numeric is None and money_nums:
                visible_candidates = [
                    (t, n, c) for (t, n, c) in money_nums
                    if not re.search(r'precio\s*s/?imp|s/imp|sin\s*imp', c, re.I)
                ]
                if visible_candidates:
                    # Choose lowest visible price (typically the offer price)
                    visible_candidates.sort(key=lambda x: x[1])
                    price_current, price_current_numeric = visible_candidates[0][0], visible_candidates[0][1]
                else:
                    # Use lowest global price as fallback
                    sorted_all = sorted(money_nums, key=lambda x: x[1])
                    price_current, price_current_numeric = sorted_all[0][0], sorted_all[0][1]

            # Determine previous price if significantly higher than current
            if price_current_numeric is not None and money_nums:
                greater = [m for m in money_nums if m[1] > price_current_numeric * 1.01]
                if greater:
                    # Choose highest previous price
                    greater.sort(key=lambda x: x[1], reverse=True)
                    price_before = greater[0][0]

            # Determine if product is discounted
            is_discounted = False
            try:
                if price_before is not None and price_current_numeric is not None:
                    pb_num = money_to_float(price_before)
                    if pb_num is not None and pb_num > price_current_numeric * 1.01:
                        is_discounted = True
            except Exception:
                is_discounted = False

            yield {
                'title': product.css('div[data-test-id="article-title"] span::text').get(),
                'url': response.urljoin(url or ''),
                'image_url': product.css('picture img::attr(src)').get(),
                'source': self.name,
                'price': price_current,
                'price_before': price_before,
                'is_discounted': is_discounted,
                'rating_str': rating_str,
                'reviews_count_str': reviews_count_str,
                'currency_code': self.currency,
                'country_code': self.country_code,
            }

        # Pagination handling
        try:
            next_href = response.css(
                'a[data-type="next"]::attr(href), '
                'a[data-test-id="pagination-next-button"]::attr(href), '
                'a[rel="next"]::attr(href)'
            ).get()

            if next_href and next_href.strip():
                next_url = response.urljoin(next_href.strip())
                if self.page_count < self.MAX_PAGES:
                    self.logger.info(f"Next Frávega page detected: {next_url}")
                    yield scrapy.Request(next_url, callback=self.parse)
                else:
                    self.logger.info("Maximum pages reached for Frávega.")
        except Exception as e:
            self.logger.debug(f"Could not resolve next page link for Frávega: {e}")

    def _compute_next_fravega_url(self, current_url):
        """
        Compute next page URL by incrementing page parameter.

        Utility method for pagination testing. Increments the 'page'
        query parameter or adds it if not present.

        Args:
            current_url: Current page URL string.

        Returns:
            str or None: Next page URL, or None if computation fails.
        """
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(current_url)
            q = parse_qs(parsed.query)
            cur = 1
            try:
                cur = int(q.get('page', ['1'])[0])
            except Exception:
                cur = 1
            q['page'] = [str(cur + 1)]
            new_query = urlencode(q, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except Exception:
            return None