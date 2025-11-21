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
        Analice la página de resultados de búsqueda y extraiga elementos de productos.

        Maneja la estructura del listado de productos de Frávega, extrayendo detalles
        información del producto, incluidos precios, calificaciones e implementación.
        lógica de paginación.

        Args:
            response: Objeto de respuesta Scrapy para la página actual.
        """
        self.page_count += 1
        self.logger.info(f"Parsing page {self.page_count}/{self.MAX_PAGES} - {response.url}")

        products = response.css('article[data-test-id="result-item"]')
        self.logger.info(f"Found {len(products)} products on Frávega page.")

        for product in products:
            # Extraer la URL básica del producto
            url = product.css('a::attr(href)').get()

            # Sólida extracción de calificaciones y reseñas con múltiples selectores alternativos
            rating_str = None
            reviews_count_str = None

            # Selectores primarios que utilizan atributos de datos.
            rating_str = product.css('[data-test-id="product-rating"] ::text').get()
            reviews_count_str = product.css('[data-test-id="product-reviews"] ::text').get()

            # Respaldo: extracto de los atributos de aria-label
            if not rating_str:
                aria = product.css('[aria-label]::attr(aria-label)').get()
                if aria:
                    m = re.search(r"([0-9]+[\.,]?[0-9]*)", aria)
                    if m:
                        rating_str = m.group(1)

            # Alternativa: selectores de calificación genéricos
            if not rating_str:
                rating_str = product.css('.rating::text, .product-rating::text, .stars::text').get()

            # Extraiga recuentos de reseñas de varios patrones de texto
            if not reviews_count_str:
                reviews_count_str = product.css(
                    'span.reviews::text, .review-count::text, .product-review-count::text'
                ).get()

            # Último recurso: busque en todo el texto palabras clave relacionadas con la reseña
            if not reviews_count_str:
                possible = product.css('::text').getall()
                if possible:
                    for t in possible:
                        if t and re.search(r"(opinione|opinion|reseñ|review|vendid|vendidos|ventas)", t, re.I):
                            reviews_count_str = t.strip()
                            break

            # Cuerdas extraídas limpias
            if rating_str:
                rating_str = rating_str.strip()
            if reviews_count_str:
                reviews_count_str = reviews_count_str.strip()

            # Registro de depuración para extracciones exitosas
            if rating_str or reviews_count_str:
                self.logger.debug(
                    f"Frávega: extracted rating='{rating_str}' "
                    f"reviews='{reviews_count_str}' url={url}"
                )

            # Extracción avanzada de precios con detección de precios actuales/anteriores
            price_container = product.css('div[data-test-id="product-price"]')

            # Recopile todos los patrones de texto monetario del contenedor de precios.
            price_texts = price_container.css('::text').getall()
            money_candidates = []

            # Construya candidatos monetarios con contexto
            for idx, t in enumerate(price_texts):
                if not t or not t.strip():
                    continue

                matches = re.findall(r'[\$€£]\s*[\d\.,]+', t)
                if not matches:
                    continue

                # Ampliar el contexto para incluir el texto vecino
                start = max(0, idx-1)
                end = min(len(price_texts), idx+2)
                ctx = ' '.join([x.strip() for x in price_texts[start:end] if x and x.strip()])

                for match in matches:
                    txt = match.strip()
                    if txt not in [c[0] for c in money_candidates]:
                        money_candidates.append((txt, ctx))

            price_current_text = None
            price_before = None

            # Prioridad: extraer el precio de oferta explícito si está disponible
            try:
                offer_span = price_container.css('span.sc-1d9b1d9e-0::text').get()
            except Exception:
                offer_span = None

            if offer_span and re.search(r'[\$€£]\s*[\d\.,]+', offer_span):
                price_current_text = offer_span.strip()
            else:
                # Extracto de tramos directos, evitando etiquetas fiscales
                spans = price_container.css('span::text').getall()
                for s in spans:
                    if not s or not s.strip():
                        continue
                    if (re.search(r'[\$€£]\s*[\d\.,]+', s) and
                        not re.search(r's/?imp|sin\s*imp|precio\s*s/?imp', s, re.I)):
                        price_current_text = s.strip()
                        break

            # Convertir cadenas monetarias a valores numéricos
            def money_to_float(s):
                """
                Convierta las cadenas de precios de Frávega en valores flotantes.

                Maneja varios formatos de números argentinos incluyendo
                Separadores decimales de estilo europeo.

                Args:
                    s: Cadena de precio (p. ej., "$ 1.234.567,89")

                Returns:
                    float or None: Valor numérico analizado
                """
                if not s:
                    return None
                s = re.sub(r'[^\d.,]', '', s)

                # Manejar diferentes patrones de separador
                if ',' in s and '.' in s:
                    # Formato europeo: 1.234,56 (miles.decimal)
                    s = s.replace('.', '').replace(',', '.')
                elif '.' in s and ',' not in s:
                    # Sólo puntos: pueden ser miles (1.234.567) o decimales (1,5)
                    parts = s.split('.')
                    if len(parts[-1]) == 3 and len(parts) > 1:
                        # Formato miles: 1.234.567
                        s = ''.join(parts)
                elif ',' in s and '.' not in s:
                    # Solo comas: pueden ser miles (1234) o decimales (1,5)
                    parts = s.split(',')
                    if len(parts[-1]) == 3 and len(parts) > 1:
                        # Formato miles: 1.234.567
                        s = ''.join(parts)
                    else:
                        # Formato decimal: 1,5
                        s = s.replace(',', '.')

                try:
                    return float(s)
                except Exception:
                    return None

            # Asigna todos los candidatos monetarios a valores numéricos
            money_nums = []
            for txt, ctx in money_candidates:
                v = money_to_float(txt)
                if v is not None:
                    money_nums.append((txt, v, ctx))

            # Determinar el precio actual
            price_current = price_current_text
            price_current_numeric = None
            if price_current:
                price_current_numeric = money_to_float(price_current)

            # Fallback: Inferir el precio actual de los candidatos monetarios
            if price_current_numeric is None and money_nums:
                visible_candidates = [
                    (t, n, c) for (t, n, c) in money_nums
                    if not re.search(r'precio\s*s/?imp|s/imp|sin\s*imp', c, re.I)
                ]
                if visible_candidates:
                    # Elija el precio más bajo visible (normalmente el precio de oferta)
                    visible_candidates.sort(key=lambda x: x[1])
                    price_current, price_current_numeric = visible_candidates[0][0], visible_candidates[0][1]
                else:
                    # Utilice el precio global más bajo como alternativa
                    sorted_all = sorted(money_nums, key=lambda x: x[1])
                    price_current, price_current_numeric = sorted_all[0][0], sorted_all[0][1]

            # Determinar el precio anterior si es significativamente más alto que el actual.
            if price_current_numeric is not None and money_nums:
                greater = [m for m in money_nums if m[1] > price_current_numeric * 1.01]
                if greater:
                    # Elige el precio anterior más alto
                    greater.sort(key=lambda x: x[1], reverse=True)
                    price_before = greater[0][0]

            # Determinar si el producto tiene descuento.
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

        # Manejo de paginación
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
        Calcule la URL de la página siguiente incrementando el parámetro de página.

        Método de utilidad para pruebas de paginación. Incrementa la 'página'
        parámetro de consulta o lo agrega si no está presente.

        Args:
            current_url: Cadena de URL de la página actual.

        Returns:
            str or None: URL de la página siguiente, o Ninguna si falla el cálculo.
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