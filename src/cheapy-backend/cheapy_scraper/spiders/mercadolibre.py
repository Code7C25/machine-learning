"""
Spider de MercadoLibre para extracción de productos.

Este spider rastrea el marketplace de MercadoLibre en múltiples países,
extrayendo información de productos incluyendo precios, calificaciones y reseñas.
Maneja paginación, normalización de precios y detección de descuentos.
"""

import scrapy
import re
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from cheapy_scraper.items import ProductItem
from config import MERCADOLIBRE_DOMAINS, COUNTRY_CURRENCIES


class MercadoLibreSpider(scrapy.Spider):
    """
    Spider de Scrapy para la plataforma de comercio electrónico MercadoLibre.

    Extrae listados de productos desde resultados de búsqueda de MercadoLibre en
    múltiples países latinoamericanos. Maneja parsing complejo de precios,
    detección de descuentos y patrones de paginación específicos de la
    interfaz de MercadoLibre.
    """

    name = "mercadolibre"
    MAX_PAGES = 2
    ITEMS_PER_PAGE = 50

    # Headers personalizados para simular solicitudes de navegador
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
    }

    def __init__(self, query="", country="AR", **kwargs):
        """
        Inicializa el spider con parámetros de búsqueda.

        Args:
            query: Término de búsqueda para consulta de productos (requerido).
            country: Código de país (ej. 'AR', 'MX', 'BR').

        Raises:
            ValueError: Si no se proporciona el parámetro query.
        """
        super().__init__(**kwargs)
        if not query:
            raise ValueError("Query parameter is required.")

        self.query = query
        self.country_code = country.upper()

        # Obtener dominio y moneda desde configuración centralizada
        domain = MERCADOLIBRE_DOMAINS.get(self.country_code, MERCADOLIBRE_DOMAINS['AR'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')

        # Construir URL de búsqueda inicial
        base_url = f"https://listado.mercadolibre.{domain}/{self.query.replace(' ', '-')}"
        self.start_urls = [base_url]
        self.page_count = 0

        self.logger.info(
            f"Initializing spider for country: {self.country_code}, "
            f"domain: {domain}, currency: {self.currency}"
        )

    def parse(self, response):
        """
        Parsea la página de resultados de búsqueda y extrae items de productos.

        Maneja la estructura HTML dinámica de MercadoLibre, extrayendo detalles de productos,
        precios, calificaciones e implementando lógica de paginación.

        Args:
            response: Objeto response de Scrapy para la página actual.
        """
        self.page_count += 1
        self.logger.info(f"Parsing page {self.page_count}/{self.MAX_PAGES} - {response.url}")

        # Iterar a través de los items de listado de productos
        for item in response.css('li.ui-search-layout__item, li.ui-search-layout__item.shops__layout-item'):
            # Extraer información básica del producto
            title = item.css('a.poly-component__title::text, h2.ui-search-item__title::text').get()
            url = item.css(
                'a.poly-component__title::attr(href), a.ui-search-link::attr(href), '
                'a.ui-search-result__content-wrapper::attr(href)'
            ).get()

            # Extraer URL de imagen con selectores de respaldo para diferentes layouts
            image_url = (
                item.css('.ui-search-result__image-container img::attr(data-src)').get() or
                item.css('.ui-search-result__image-container img::attr(src)').get() or
                item.css('.ui-search-result__image img::attr(data-src)').get() or
                item.css('.ui-search-result__image img::attr(src)').get() or
                item.css('picture source::attr(srcset)').get() or
                item.css('picture img::attr(src)').get() or
                item.css('.poly-card__portada img::attr(data-src)').get() or
                item.css('.poly-card__portada img::attr(src)').get()
            )

            # Manejar atributos srcset tomando la primera URL
            if image_url and ' ' in image_url:
                image_url = image_url.split(' ')[0].strip()

            # Extraer calificación y conteo de reseñas desde componentes compactos de reseñas
            rating_str = item.css('span.poly-reviews__rating::text, .ui-search-reviews__rating-number::text').get()
            review_labels = item.css('span.poly-component__review-compacted .poly-phrase-label::text').getall()
            rating_str = review_labels[0].strip() if len(review_labels) > 0 else None
            reviews_count_str = review_labels[1].strip() if len(review_labels) > 1 else None

            # Registrar conteos de reseñas sospechosos para depuración
            try:
                if reviews_count_str:
                    compact = re.sub(r"[^0-9]", "", reviews_count_str)
                    if compact:
                        num = int(compact)
                        if num > 1000000:
                            self.logger.warning(
                                f"Large review count detected: {reviews_count_str!r} "
                                f"title={title!r} url={url!r} page={response.url!r}"
                            )
                    if 'mil' in reviews_count_str.lower():
                        self.logger.debug(
                            f"Review count contains 'mil': {reviews_count_str!r} "
                            f"title={title!r} url={url!r}"
                        )
            except Exception:
                pass  # No interrumpa el análisis ante errores de registro

            # Extraer componentes de precio con múltiples selectores para diferentes layouts
            price_symbol = item.css('.andes-money-amount__currency-symbol::text').get()
            price_fraction = item.css('.andes-money-amount__fraction::text').get()
            price_fraction_discount = item.css('div.poly-price__current .andes-money-amount__fraction::text').get()
            price_fraction_normal = item.css('.ui-search-price .andes-money-amount__fraction::text').get()
            final_price_fraction = price_fraction_discount or price_fraction_normal or price_fraction
            price_full_str = f"{price_symbol or ''}{final_price_fraction or ''}"

            # Normalizar y validar URL del producto
            normalized_url = None
            if url:
                try:
                    parsed = urlparse(url)
                    normalized_url = urlunparse(parsed._replace(query='', fragment=''))
                except Exception:
                    normalized_url = url

            # Omitir items sin imágenes (típicamente anuncios o módulos especiales)
            if not image_url:
                continue

            # Omitir URLs de seguimiento/redireccionamiento que no son páginas de productos navegables
            if normalized_url and self._is_bad_meli_url(normalized_url):
                continue

            # Inicializar item de producto con datos extraídos
            product = ProductItem()
            product['title'] = title
            product['url'] = normalized_url
            product['image_url'] = image_url
            product['source'] = self.name
            product['price'] = price_full_str if final_price_fraction else None

            # Análisis avanzado de precios para precios actuales y anteriores
            price_numeric = None
            price_before = None
            price_before_numeric = None
            discount_label_text = None

            # Convertir el precio actual a valor numérico
            try:
                if final_price_fraction:
                    price_numeric = self.money_to_float(final_price_fraction)
            except Exception:
                pass

            #Extraer información anterior de precios y descuentos.
            try:
                prev_fraction = (
                    item.css('s.andes-money-amount--previous .andes-money-amount__fraction::text').get() or
                    item.css('s.andes-money-amount .andes-money-amount__fraction::text').get()
                )
                discount_label_text = item.css(
                    '.andes-money-amount__discount::text, .poly-price__disc_label::text'
                ).get()
                if prev_fraction:
                    price_before = f"{price_symbol or ''}{prev_fraction}"
                    price_before_numeric = self.money_to_float(prev_fraction)
            except Exception:
                pass

            # Heurística alternativa: analiza todo el texto monetario del artículo
            try:
                money_candidates = item.css('*::text').re(r'[\$€£]\s*[\d\.,]+')
                money_candidates = [m.strip() for m in money_candidates if m and m.strip()]

                # Eliminar duplicados manteniendo el orden
                unique_money = []
                for m in money_candidates:
                    if m not in unique_money:
                        unique_money.append(m)

                # Convertir todos los candidatos a valores numéricos
                money_numeric = []
                for text in unique_money:
                    try:
                        num = self.money_to_float(text)
                        if num is not None:
                            money_numeric.append((text, num))
                    except Exception:
                        pass

                # Inferir el precio actual si los selectores directos lo omitieron
                if price_numeric is None and money_numeric:
                    price_numeric = min([n for _, n in money_numeric])
                    price_full_str = money_numeric[0][0]

                # Detectar heurísticamente el precio anterior si fallaron los selectores directos
                if price_before_numeric is None and price_numeric and len(money_numeric) > 1:
                    for text, num in money_numeric:
                        if num > price_numeric * 1.01:  # Más del 1% superior al actual
                            price_before = text
                            price_before_numeric = num
                            break
            except Exception:
                pass

            # Complete el artículo del producto con información de precios
            product['price'] = price_full_str if price_numeric else None
            product['price_before'] = price_before
            product['rating_str'] = rating_str
            product['reviews_count_str'] = reviews_count_str
            product['currency_code'] = self.currency
            product['country_code'] = self.country_code
            product['price_numeric'] = price_numeric
            product['price_before_numeric'] = price_before_numeric

            # Determinar si el producto tiene descuento.
            is_discounted = False
            try:
                if discount_label_text:
                    is_discounted = True
                elif price_before_numeric is not None and price_numeric is not None:
                    if price_before_numeric > price_numeric * 1.01:
                        is_discounted = True
            except Exception:
                is_discounted = False
            product['is_discounted'] = is_discounted

            yield product

        # Handle pagination: Pruebe primero con el botón Siguiente y luego recurra al cálculo de URL.
        if self.page_count < self.MAX_PAGES:
            next_url = self._extract_next_link(response)
            if not next_url:
                next_url = self._compute_next_meli_url(response.url)

            if next_url:
                self.logger.info(f"Next page detected: {next_url}")
                yield scrapy.Request(
                    url=next_url,
                    headers=self.custom_headers,
                    callback=self.parse,
                )
            else:
                self.logger.info("No next page link found or could be computed.")

    def start_requests(self):
        """
        Genere solicitudes iniciales con encabezados personalizados.

        Garantiza que todas las solicitudes, incluida la primera, utilicen información coherente
        encabezados para evitar la detección.
        """
        for url in self.start_urls:
            yield scrapy.Request(url, headers=self.custom_headers, callback=self.parse)

    def money_to_float(self, money_str):
        """
        Convertir cadenas monetarias en valores flotantes.

        Maneja formatos de números europeos (1.234,56) y estadounidenses (1.234,56).
        detectar automáticamente separadores decimales según el contexto.

        Args:
            money_str: Cadena que contiene símbolo de moneda y valor numérico.

        Returns:
            float or None: Valor numérico analizado o Ninguno si falla el análisis.
        """
        if not money_str or not isinstance(money_str, str):
            return None

        # Eliminar símbolos de moneda y espacios en blanco
        cleaned = re.sub(r'[\$€£\s]', '', money_str.strip())

        # Devuelve Ninguno si no se encuentran dígitos
        if not re.search(r'\d', cleaned):
            return None

        # Encuentre el último separador (punto decimal potencial)
        last_sep_pos = max(cleaned.rfind(','), cleaned.rfind('.'))

        if last_sep_pos == -1:
            # No se encontró separador, tratar como entero
            try:
                return float(cleaned)
            except ValueError:
                return None

        # Dividir en partes antes y después del último separador
        before_sep = cleaned[:last_sep_pos]
        after_sep = cleaned[last_sep_pos + 1:]

        # Determinar el tipo de separador según la longitud de la parte decimal
        if len(after_sep) == 2:
            # Formato europeo: separador de miles es punto, decimal es coma
            thousands_part = before_sep.replace('.', '')
            try:
                return float(thousands_part + '.' + after_sep)
            except ValueError:
                return None
        elif len(after_sep) >= 3:
            # Formato estadounidense: el último separador es separador de miles
            thousands_part = before_sep.replace(',', '') + after_sep.replace('.', '')
            try:
                return float(thousands_part)
            except ValueError:
                return None
        else:
            # Caso ambiguo: intentar normalizaciones comunes
            try:
                normalized = cleaned.replace(',', '.')
                return float(normalized)
            except ValueError:
                return None

    def _extract_next_link(self, response):
        """
        Extraiga la URL de la página siguiente de los controles de paginación de MercadoLibre.

        Intenta encontrar el enlace del botón "Siguiente" en la sección de paginación.

        Args:
            response: Respuesta de la página actual.

        Returns:
            str or None: URL absoluta de la siguiente página, o Ninguno si no se encuentra.
        """
        try:
            href = response.css(
                'li.andes-pagination__button.andes-pagination__button--next a::attr(href), '
                'a.andes-pagination__link[title="Siguiente"]::attr(href)'
            ).get()
            if href and href.strip():
                return response.urljoin(href.strip())
        except Exception:
            pass
        return None

    def _compute_next_meli_url(self, current_url):
        """
        Calcular la URL de la página siguiente cuando falla la extracción del enlace directo.

        Implementa la lógica de paginación de reserva para los patrones de URL de MercadoLibre:
        - Actualiza los parámetros _Desde_ en la ruta
        - Agrega parámetros de paginación a la cadena de consulta
        Args:
            current_url: URL de la página actual como cadena.

        Returns:
            str or None: URL calculada de la página siguiente, o Ninguno si el cálculo falla.
        """
        try:
            parsed = urlparse(current_url)
            path = parsed.path or ''

            # Caso 1: actualizar el parámetro _Desde_ existente en la ruta
            m = re.search(r"(_Desde_)(\d+)", path)
            if m:
                prefix, num = m.group(1), int(m.group(2))
                new_num = num + self.ITEMS_PER_PAGE
                new_path = re.sub(r"(_Desde_)\d+", f"{prefix}{new_num}", path)
                return urlunparse(parsed._replace(path=new_path, query='', fragment=''))

            # Caso 2: Agregar parámetro _Desde_ al slug de la ruta
            if path and not path.endswith('/'):
                start = self.ITEMS_PER_PAGE + 1
                new_path = f"{path}_Desde_{start}_NoIndex_True"
                return urlunparse(parsed._replace(path=new_path, query='', fragment=''))

            # Caso 3: Usar parámetro de consulta como último recurso
            q = parse_qs(parsed.query)
            cur = 0
            try:
                cur = int(q.get('_Desde', ['0'])[0])
            except Exception:
                cur = 0
            q['_Desde'] = [str(cur + self.ITEMS_PER_PAGE)]
            new_query = urlencode(q, doseq=True)
            return urlunparse(parsed._replace(query=new_query, fragment=''))
        except Exception:
            return None

    def _is_bad_meli_url(self, url):
        """
        Detectar URL de seguimiento/redireccionamiento que no sean páginas de productos navegables.

        Filtra los dominios de seguimiento de clics de MercadoLibre y las URL de redireccionamiento
        que no conducen a páginas de productos reales.

        Args:
            url: Cadena de URL para evaluar.

        Returns:
            bool: Verdadero si se debe omitir la URL; Falso en caso contrario.
        """
        try:
            p = urlparse(url)
            host = (p.netloc or '').lower()
            path = (p.path or '').lower()
            if 'click1.mercadolibre' in host or 'mclics' in path:
                return True
            return False
        except Exception:
            return True