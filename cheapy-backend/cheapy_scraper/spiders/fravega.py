import re
import scrapy
from config import COUNTRY_CURRENCIES

class FravegaSpider(scrapy.Spider):
    name = "fravega"

    # No se necesita Playwright.
    
    def __init__(self, query="", country="AR", **kwargs):
        super().__init__(**kwargs)
        if country.upper() != 'AR':
            self.logger.warning(f"El spider de Fravega solo soporta 'AR'. Se ignora el país '{country}'.")
        
        self.query = query
        self.country_code = "AR"
        self.currency = COUNTRY_CURRENCIES.get(self.country_code)
        self.start_urls = [f"https://www.fravega.com/l/?keyword={self.query.replace(' ', '%20')}"]
        self.logger.info(f"Iniciando Fravega spider para query: '{self.query}'")

    def parse(self, response):
        # Selector para el contenedor principal de cada producto
        products = response.css('article[data-test-id="result-item"]')
        self.logger.info(f"Se encontraron {len(products)} productos en la página de Fravega.")
        
        for product in products:
            # La URL es el 'href' del primer enlace 'a' que se encuentra dentro del artículo
            url = product.css('a::attr(href)').get()
            
            # --- Extracción robusta de rating y reviews ---
            # Intentamos múltiples selectores/atributos porque la estructura puede cambiar.
            rating_str = None
            reviews_count_str = None

            # 1) Selector explícito por data-test-id si existe
            rating_str = product.css('[data-test-id="product-rating"] ::text').get()
            reviews_count_str = product.css('[data-test-id="product-reviews"] ::text').get()

            # 2) Atributos aria (ej: aria-label="4.7 de 5")
            if not rating_str:
                aria = product.css('[aria-label]::attr(aria-label)').get()
                if aria:
                    # extraer algo como '4.7' de '4.7 de 5'
                    m = re.search(r"([0-9]+[\.,]?[0-9]*)", aria)
                    if m:
                        rating_str = m.group(1)

            # 3) Selectores genéricos conocidos
            if not rating_str:
                rating_str = product.css('.rating::text, .product-rating::text, .stars::text').get()

            # Reviews count: textos como '12 opiniones', '(12)', '1.2k', '1,2 mil'
            if not reviews_count_str:
                # textos dentro de etiquetas que suelen usar 'opiniones' o 'reseñas'
                reviews_count_str = product.css('span.reviews::text, .review-count::text, .product-review-count::text').get()

            # A veces el conteo está dentro del título o en un pequeño label
            if not reviews_count_str:
                # buscar dentro de etiquetas pequeñas dentro del producto
                possible = product.css('::text').getall()
                if possible:
                    for t in possible:
                        if t and re.search(r"(opinione|opinion|reseñ|review|vendid|vendidos|ventas)", t, re.I):
                            reviews_count_str = t.strip()
                            break

            # Normalizar strings vacíos
            if rating_str:
                rating_str = rating_str.strip()
            if reviews_count_str:
                reviews_count_str = reviews_count_str.strip()

            # Log debug breve
            if rating_str or reviews_count_str:
                self.logger.debug(f"Fravega: encontrado rating='{rating_str}' reviews='{reviews_count_str}' url={url}")

            # Detectar posibles precios dentro del contenedor de precio y distinguir current vs before
            price_container = product.css('div[data-test-id="product-price"]')
            
            # Recolectar TODOS los textos del contenedor de precio para encontrar valores monetarios
            price_texts = price_container.css('::text').getall()
            money_candidates = []
            # Construir candidatos monetarios y contexto ampliado (vecinos)
            for idx, t in enumerate(price_texts):
                if not t or not t.strip():
                    continue
                # Buscar patrones monetarios: $1.234,56 o $1,234.56 etc.
                matches = re.findall(r'[\$€£]\s*[\d\.,]+', t)
                if not matches:
                    continue
                # ampliar contexto: tomar token anterior y siguiente para capturar etiquetas tipo 'Precio s/imp.'
                start = max(0, idx-1)
                end = min(len(price_texts), idx+2)
                ctx = ' '.join([x.strip() for x in price_texts[start:end] if x and x.strip()])
                for match in matches:
                    txt = match.strip()
                    # Evitar duplicados
                    if txt not in [c[0] for c in money_candidates]:
                        money_candidates.append((txt, ctx))
            
            price_current_text = None
            price_before = None

            # PRIORIDAD: intentar extraer explícitamente el precio de oferta visible
            # (clase observada en la página: 'sc-1d9b1d9e-0' — si existe, preferirla)
            try:
                offer_span = price_container.css('span.sc-1d9b1d9e-0::text').get()
            except Exception:
                offer_span = None

            if offer_span and re.search(r'[\$€£]\s*[\d\.,]+', offer_span):
                price_current_text = offer_span.strip()
            else:
                # Buscar en los spans directos del contenedor evitando líneas tipo 'Precio s/imp.'
                spans = price_container.css('span::text').getall()
                for s in spans:
                    if not s or not s.strip():
                        continue
                    if re.search(r'[\$€£]\s*[\d\.,]+', s) and not re.search(r's/?imp|sin\s*imp|precio\s*s/?imp', s, re.I):
                        price_current_text = s.strip()
                        break

            # Normalizar función para convertir "$ 1.234.567,89" -> float
            def money_to_float(s):
                if not s: return None
                s = re.sub(r'[^\d.,]', '', s)
                # Fravega usa coma decimal en algunos textos (formato europeo)
                if ',' in s and '.' in s:
                    # Ambos presentes: formato 1.234,56 (mil.decimal)
                    s = s.replace('.', '').replace(',', '.')
                elif '.' in s and ',' not in s:
                    # Solo puntos: pueden ser miles (1.234.567) o decimal (1.5)
                    parts = s.split('.')
                    if len(parts[-1]) == 3 and len(parts) > 1:
                        # Es formato de miles: 1.234.567
                        s = ''.join(parts)
                    else:
                        # Podría ser decimal, mantener como está
                        pass
                elif ',' in s and '.' not in s:
                    # Solo comas: pueden ser miles (1,234) o decimal (1,5)
                    parts = s.split(',')
                    if len(parts[-1]) == 3 and len(parts) > 1:
                        # Es formato de miles: 1,234,567
                        s = ''.join(parts)
                    else:
                        # Es decimal
                        s = s.replace(',', '.')
                try:
                    return float(s)
                except Exception:
                    return None

            # Mapear candidatos a valores numéricos (conservando contexto)
            money_nums = []
            for txt, ctx in money_candidates:
                v = money_to_float(txt)
                if v is not None:
                    money_nums.append((txt, v, ctx))

            # Determinar price_current_numeric
            price_current = price_current_text
            price_current_numeric = None
            if price_current:
                price_current_numeric = money_to_float(price_current)

            # Si no encontramos current por selector explícito ni por spans directos, inferir: preferir valores visibles (no 'Precio s/imp.')
            if price_current_numeric is None and money_nums:
                # Filtrar candidatos que parecen ser 'precio sin impuestos' por contexto
                visible_candidates = [ (t, n, c) for (t, n, c) in money_nums if not re.search(r'precio\s*s/?imp|s/imp|sin\s*imp', c, re.I) ]
                if visible_candidates:
                    # Elegir el menor valor entre los visibles (el precio en oferta suele ser menor que el original)
                    visible_candidates.sort(key=lambda x: x[1])
                    price_current, price_current_numeric = visible_candidates[0][0], visible_candidates[0][1]
                else:
                    # Si no hay candidatos visibles, usar el menor global
                    sorted_all = sorted(money_nums, key=lambda x: x[1])
                    price_current, price_current_numeric = sorted_all[0][0], sorted_all[0][1]

            # Determinar price_before SOLO si hay un valor estrictamente mayor a current
            price_before = None
            if price_current_numeric is not None and money_nums:
                # Filtrar valores que son estrictamente mayores (considerar el tercer elemento de la tupla)
                greater = [m for m in money_nums if m[1] > price_current_numeric * 1.01]
                if greater:
                    # elegir el máximo (precio original mayor)
                    greater.sort(key=lambda x: x[1], reverse=True)
                    price_before = greater[0][0]

            # Señal genérica: marcar si está en oferta (no calculamos % aquí)
            is_discounted = False
            try:
                if price_before is not None and price_current_numeric is not None:
                    pb_num = money_to_float(price_before)
                    if pb_num is not None and pb_num > price_current_numeric * 1.01:
                        is_discounted = True
            except Exception:
                is_discounted = False

            yield {
                # Selector para el título
                'title': product.css('div[data-test-id="article-title"] span::text').get(),
                'url': response.urljoin(url or ''),

                # Selector para la imagen (buscamos la img dentro de la etiqueta picture)
                'image_url': product.css('picture img::attr(src)').get(),

                'source': self.name,

                # Selector para el precio
                'price': price_current,
                # Intentar detectar precio anterior / oferta
                'price_before': price_before,
                'is_discounted': is_discounted,

                'rating_str': rating_str,
                'reviews_count_str': reviews_count_str,
                'currency_code': self.currency,
                'country_code': self.country_code,
            }