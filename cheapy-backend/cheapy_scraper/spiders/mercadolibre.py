# cheapy-backend/cheapy_scraper/spiders/mercadolibre.py

import scrapy
import re
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode 
from cheapy_scraper.items import ProductItem
# Se importan las configuraciones centralizadas
from config import MERCADOLIBRE_DOMAINS, COUNTRY_CURRENCIES

class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"
    MAX_PAGES = 2
    # MercadoLibre suele paginar en saltos de 50 (ej.: _Desde_51, _Desde_101, ...)
    ITEMS_PER_PAGE = 50
    
    # El diccionario 'meli_domains' se ha movido a config.py
    
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
        # ... resto de tus headers ...
    }

    def __init__(self, query="", country="AR", **kwargs):
        super().__init__(**kwargs)
        if not query:
            raise ValueError("El argumento 'query' es obligatorio.")
        
        self.query = query
        self.country_code = country.upper()
        
        # Se usan las variables importadas desde config.py
        domain = MERCADOLIBRE_DOMAINS.get(self.country_code, MERCADOLIBRE_DOMAINS['AR'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD') # Usamos USD como fallback genérico
        
        base_url = f"https://listado.mercadolibre.{domain}/{self.query.replace(' ', '-')}"
        self.start_urls = [base_url]
        self.page_count = 0
        
        self.logger.info(f"Iniciando spider para País: {self.country_code}, Dominio: {domain}, Moneda: {self.currency}")

    def parse(self, response):
        self.page_count += 1
        self.logger.info(f"Parseando página {self.page_count}/{self.MAX_PAGES} - {response.url}")

        for item in response.css('li.ui-search-layout__item'):
            title = item.css('a.poly-component__title::text, h2.ui-search-item__title::text').get()
            url = item.css('a.poly-component__title::attr(href), a.ui-search-link::attr(href)').get()

            # Selector de imagen EXACTAMENTE como lo tenías
            image_url = item.css('.ui-search-result__image-container img::attr(data-src)').get() or \
            item.css('.ui-search-result__image-container img::attr(src)').get() or \
            item.css('.poly-card__portada img::attr(data-src)').get() or \
            item.css('.poly-card__portada img::attr(src)').get()

            rating_str = item.css('span.poly-reviews__rating::text, .ui-search-reviews__rating-number::text').get()
            # Nuevo selector basado en la estructura actual de MercadoLibre
            # Muchas tarjetas compactas usan el span.poly-component__review-compacted
            # que contiene dos spans .poly-phrase-label: [rating, "| +50 vendidos"/sales]
            review_labels = item.css('span.poly-component__review-compacted .poly-phrase-label::text').getall()
            rating_str = review_labels[0].strip() if len(review_labels) > 0 else None
            reviews_count_str = review_labels[1].strip() if len(review_labels) > 1 else None

            # Loguear casos sospechosos para ayudar a depuración upstream
            try:
                if reviews_count_str:
                    # Extraer dígitos compactos para revisar magnitude
                    compact = re.sub(r"[^0-9]", "", reviews_count_str)
                    if compact:
                        num = int(compact)
                        if num > 1000000:
                            self.logger.warning(f"[mercadolibre spider] reviews_count_str grande extraído: {reviews_count_str!r} title={title!r} url={url!r} page={response.url!r}")
                    # También reportar casos donde aparece la palabra 'mil' (para comparar)
                    if 'mil' in reviews_count_str.lower():
                        self.logger.debug(f"[mercadolibre spider] reviews_count_str contiene 'mil': {reviews_count_str!r} title={title!r} url={url!r}")
            except Exception:
                # No queremos que un fallo de logging rompa el spider
                pass
            
            price_symbol = item.css('.andes-money-amount__currency-symbol::text').get()
            price_fraction = item.css('.andes-money-amount__fraction::text').get()
            price_fraction_discount = item.css('div.poly-price__current .andes-money-amount__fraction::text').get()
            price_fraction_normal = item.css('.ui-search-price .andes-money-amount__fraction::text').get()
            final_price_fraction = price_fraction_discount or price_fraction_normal or price_fraction
            price_full_str = f"{price_symbol or ''}{final_price_fraction or ''}"

            product = ProductItem()
            product['title'] = title
            # Normalizamos la URL: removemos query y fragment para evitar duplicados
            if url:
                try:
                    parsed = urlparse(url)
                    normalized_url = urlunparse(parsed._replace(query='', fragment=''))
                except Exception:
                    normalized_url = url
            else:
                normalized_url = None
            product['url'] = normalized_url
            product['image_url'] = image_url
            product['source'] = self.name
            product['price'] = price_full_str if final_price_fraction else None
            
            # ========== IMPROVED PRICE BEFORE DETECTION (ROBUST) ==========
            price_numeric = None
            price_before = None
            price_before_numeric = None
            discount_label_text = None
            
            # Extract current price as numeric
            try:
                if final_price_fraction:
                    price_numeric = self.money_to_float(final_price_fraction)
            except Exception:
                pass
            
            # Try direct selectors for previous price and discount label (more reliable)
            try:
                prev_fraction = item.css('s.andes-money-amount--previous .andes-money-amount__fraction::text').get() or \
                                item.css('s.andes-money-amount .andes-money-amount__fraction::text').get()
                discount_label_text = item.css('.andes-money-amount__discount::text, .poly-price__disc_label::text').get()
                if prev_fraction:
                    price_before = f"{price_symbol or ''}{prev_fraction}"
                    price_before_numeric = self.money_to_float(prev_fraction)
            except Exception:
                pass

            # Collect all monetary text patterns from item container (fallback heuristic)
            try:
                money_candidates = item.css('*::text').re(r'[\$€£]\s*[\d\.,]+')
                money_candidates = [m.strip() for m in money_candidates if m and m.strip()]
                
                # Remove duplicates while preserving order
                unique_money = []
                for m in money_candidates:
                    if m not in unique_money:
                        unique_money.append(m)
                
                # Convert all candidates to numeric values
                money_numeric = []
                for text in unique_money:
                    try:
                        num = self.money_to_float(text)
                        if num is not None:
                            money_numeric.append((text, num))
                    except Exception:
                        pass
                
                # Infer current price if selector missed it
                if price_numeric is None and money_numeric:
                    price_numeric = min([n for _, n in money_numeric])
                    price_full_str = money_numeric[0][0]  # Use first candidate as price text
                
                # If direct selector didn't find previous price, detect it heuristically
                if price_before_numeric is None and price_numeric and len(money_numeric) > 1:
                    for text, num in money_numeric:
                        if num > price_numeric * 1.01:  # >1% higher than current
                            price_before = text
                            price_before_numeric = num
                            break
            except Exception:
                pass
            
            product['price'] = price_full_str if price_numeric else None
            product['price_before'] = price_before
            product['rating_str'] = rating_str
            product['reviews_count_str'] = reviews_count_str
            product['currency_code'] = self.currency
            product['country_code'] = self.country_code

            # Asignar numerics cuando estén disponibles
            product['price_numeric'] = price_numeric
            product['price_before_numeric'] = price_before_numeric

            # Señal genérica: marcar si está en oferta (no calcular % aquí)
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

        # --- Paginación: primero intenta seguir el botón "Siguiente", luego fallback por patrón _Desde_ ---
        if self.page_count < self.MAX_PAGES:
            next_url = self._extract_next_link(response)
            if not next_url:
                next_url = self._compute_next_meli_url(response.url)

            if next_url:
                self.logger.info(f"Siguiente página detectada: {next_url}")
                yield scrapy.Request(
                    url=next_url,
                    headers=self.custom_headers,
                    callback=self.parse,
                )
            else:
                self.logger.info("No se encontró enlace de 'Siguiente' ni se pudo calcular siguiente URL.")

    def start_requests(self):
        for url in self.start_urls:
            # Aseguramos que la primera solicitud también use los headers
            yield scrapy.Request(url, headers=self.custom_headers, callback=self.parse)
    
    def money_to_float(self, money_str):
        """
        Normalize European (1.234,56) and US (1,234.56) numeric formats to float.
        Handles currency symbols and common separators.
        
        Args:
            money_str: String like "$1.234,56" or "€1,234.56"
            
        Returns:
            float: Parsed numeric value, or None if parsing fails
        """
        if not money_str or not isinstance(money_str, str):
            return None
        
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[\$€£\s]', '', money_str.strip())
        
        # If no digits found, return None
        if not re.search(r'\d', cleaned):
            return None
        
        # Separate the last separator from the rest
        # The last separator (comma or dot) is likely the decimal separator
        last_sep_pos = max(cleaned.rfind(','), cleaned.rfind('.'))
        
        if last_sep_pos == -1:
            # No separator found, treat as integer
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        # Extract part before and after last separator
        before_sep = cleaned[:last_sep_pos]
        after_sep = cleaned[last_sep_pos + 1:]
        
        # Determine separator type based on length of decimal part
        # If after_sep has 2 digits: likely decimal separator
        # If after_sep has 3+ digits: likely thousands separator (so this is thousands, not decimal)
        if len(after_sep) == 2:
            # European format: 1.234,56 → thousands sep is dot, decimal is comma
            # Clean thousands separators from before_sep
            thousands_part = before_sep.replace('.', '')
            try:
                return float(thousands_part + '.' + after_sep)
            except ValueError:
                return None
        elif len(after_sep) >= 3:
            # US format: 1,234.56 or 1,234,567 → last sep is thousands
            # Treat the part after as thousands grouping
            thousands_part = before_sep.replace(',', '') + after_sep.replace('.', '')
            try:
                return float(thousands_part)
            except ValueError:
                return None
        else:
            # Ambiguous, try to parse as-is
            try:
                # Replace common separators
                normalized = cleaned.replace(',', '.')
                return float(normalized)
            except ValueError:
                return None

    # ===================== Helpers de paginación MercadoLibre =====================
    def _extract_next_link(self, response) -> str | None:
        """
        Busca el enlace 'Siguiente' en la paginación de MercadoLibre y devuelve la URL absoluta.
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

    def _compute_next_meli_url(self, current_url: str) -> str | None:
        """
        Fallback cuando no hay enlace 'Siguiente':
        - Si la URL contiene patrón en PATH tipo *_Desde_51*, incrementa por ITEMS_PER_PAGE.
        - Si no lo contiene, agrega *_Desde_{ITEMS_PER_PAGE+1}_NoIndex_True* al final del slug.
        - Como último recurso, añade query _Desde=... (algunos listados lo aceptan).
        """
        try:
            parsed = urlparse(current_url)
            path = parsed.path or ''

            # Caso 1: patrón en el path
            m = re.search(r"(_Desde_)(\d+)", path)
            if m:
                prefix, num = m.group(1), int(m.group(2))
                new_num = num + self.ITEMS_PER_PAGE
                new_path = re.sub(r"(_Desde_)\d+", f"{prefix}{new_num}", path)
                return urlunparse(parsed._replace(path=new_path, query='', fragment=''))

            # Caso 2: no tiene _Desde_ en path. Agregarlo al final del último segmento del slug
            # Ej.: /electronica-audio-video/televisores/tv -> /.../tv_Desde_51_NoIndex_True
            if path and not path.endswith('/'):
                start = self.ITEMS_PER_PAGE + 1  # 51 si ITEMS_PER_PAGE=50
                new_path = f"{path}_Desde_{start}_NoIndex_True"
                return urlunparse(parsed._replace(path=new_path, query='', fragment=''))

            # Caso 3: query param como último recurso
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