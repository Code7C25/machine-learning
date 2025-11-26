import re
import scrapy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from cheapy_scraper.items import ProductItem
from config import COUNTRY_CURRENCIES
from scrapy_playwright.page import PageMethod


class MegatoneSpider(scrapy.Spider):
    name = "megatone"
    allowed_domains = ["megatone.net", "www.megatone.net"]
    MAX_PAGES = 1
    
    # Forzar Playwright solo para este spider
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        # Opciones Playwright específicas
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": False},
        "PLAYWRIGHT_CONTEXT_ARGS": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "es-AR",
            "java_script_enabled": True,
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            },
            "record_har_path": "megatone.har",
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 45000,
        "PLAYWRIGHT_PAGE_GOTO_OPTIONS": {"wait_until": "domcontentloaded", "timeout": 45000},
    }

    def __init__(self, query="", country="AR", **kwargs):
        super().__init__(**kwargs)
        if country.upper() != 'AR':
            self.logger.warning(f"El spider de Megatone solo soporta 'AR'. Se ignora el país '{country}'.")

        self.query = query or "tv"
        self.country_code = "AR"
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, "ARS")
        self.start_urls = [f"https://www.megatone.net/resultados-busqueda?q={self.query}"]
        self.page_count = 0

    def start_requests(self):
        for url in self.start_urls:
            # Primera carga con Playwright (sin clicks), para obtener página 1
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "clicks": 0,
                    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded", "timeout": 45000},
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_selector", "a.producto", state="attached", timeout=25000),
                    ],
                },
            )

    def parse(self, response):
        self.page_count += 1
        self.logger.info(f"Megatone: Parseando página {self.page_count}/{self.MAX_PAGES} - {response.url}")

        # Cada producto aparece anclado en un <a class="producto" href="..."> ... </a>
        for prod in response.css('a.producto'):
            href = prod.attrib.get('href')
            url = response.urljoin(href) if href else None

            # Título: tomar todos los textos dentro de h3 (incluye <span>marca)
            title_texts = prod.css('div.nombre h3 ::text').getall()
            title = ' '.join(t.strip() for t in title_texts if t and t.strip()) or None

            image_url = prod.css('div.imagen img::attr(src)').get()

            # Precios
            price_before_text = prod.css('div.precios .lista::text').get()
            price_current_text = prod.css('div.precios .promocional::text').get() or price_before_text
            discount_label = prod.css('div.precios .porcentaje-off::text').get()

            price_numeric = self.money_to_float(price_current_text)
            price_before_numeric = self.money_to_float(price_before_text) if price_before_text else None

            is_discounted = False
            try:
                if price_before_numeric and price_numeric and price_before_numeric > price_numeric * 1.01:
                    is_discounted = True
                elif discount_label and price_before_numeric and price_numeric:
                    is_discounted = True
            except Exception:
                is_discounted = False

            item = ProductItem()
            item['title'] = title
            item['url'] = url
            item['image_url'] = image_url
            item['source'] = self.name
            item['price'] = price_current_text.strip() if price_current_text else None
            item['price_before'] = price_before_text.strip() if price_before_text else None
            item['price_numeric'] = price_numeric
            item['price_before_numeric'] = price_before_numeric
            item['is_discounted'] = is_discounted
            item['rating_str'] = None
            item['reviews_count_str'] = None
            item['currency_code'] = self.currency
            item['country_code'] = self.country_code

            yield item

        # Paginación (con click usando Playwright si no hay cambio de URL)
        if self.page_count < self.MAX_PAGES:
            clicks = response.meta.get("clicks", 0)

            # 1) Si existe rel=next o similar, úsalo (por si Megatone alguna vez expone paginación real)
            next_url = response.css('a[rel="next"]::attr(href), link[rel="next"]::attr(href)').get()
            if next_url:
                next_url = response.urljoin(next_url)
                self.logger.info(f"Megatone: siguiente página por href -> {next_url}")
                yield scrapy.Request(
                    next_url,
                    callback=self.parse,
                    meta={
                        "playwright": True,
                        "clicks": clicks,
                        "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded", "timeout": 45000},
                    },
                )
                return

            # 2) Si no hay next_url, usar click en el botón 'Siguiente' y volver a parsear
            if clicks < (self.MAX_PAGES - 1):
                self.logger.info("Megatone: intentando avanzar con click en 'div.siguiente.p-3'")
                yield scrapy.Request(
                    response.url,
                    callback=self.parse,
                    meta={
                        "playwright": True,
                        "clicks": clicks + 1,
                        "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded", "timeout": 45000},
                        "playwright_page_methods": [
                            PageMethod("wait_for_selector", "div.siguiente.p-3", timeout=8000),
                            PageMethod("evaluate", "() => window.scrollTo(0, document.body.scrollHeight)"),
                            PageMethod("click", "div.siguiente.p-3"),
                            # Esperar un poco para que carguen más productos.
                            PageMethod("wait_for_timeout", 4000),
                            # Asegurar que hay productos visibles post click
                            PageMethod("wait_for_selector", "a.producto", timeout=12000),
                        ],
                    },
                    dont_filter=True,
                )
            else:
                self.logger.info("Megatone: máximo de páginas alcanzado (por clicks)")

    def money_to_float(self, money_str):
        if not money_str or not isinstance(money_str, str):
            return None
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[\$€£\s]', '', money_str.strip())
        if not re.search(r'\d', cleaned):
            return None
        # Detectar separadores
        last_sep_pos = max(cleaned.rfind(','), cleaned.rfind('.'))
        if last_sep_pos == -1:
            try:
                return float(cleaned)
            except ValueError:
                return None
        before_sep = cleaned[:last_sep_pos]
        after_sep = cleaned[last_sep_pos + 1:]
        if len(after_sep) == 2:
            thousands_part = before_sep.replace('.', '')
            try:
                return float(thousands_part + '.' + after_sep)
            except ValueError:
                return None
        elif len(after_sep) >= 3:
            thousands_part = before_sep.replace(',', '') + after_sep.replace('.', '')
            try:
                return float(thousands_part)
            except ValueError:
                return None
        else:
            try:
                normalized = cleaned.replace(',', '.')
                return float(normalized)
            except ValueError:
                return None

    def _compute_next_megatone_url(self, current_url: str) -> str | None:
        """
        Intento genérico: incrementar 'page' o 'p' en la query si existe; si no, agregar page=2.
        Nota: Si el sitio usa botón JS sin URL distinta, hará falta usar Playwright para clickear el botón.
        """
        try:
            parsed = urlparse(current_url)
            q = parse_qs(parsed.query)
            key = None
            for k in ['page', 'p', 'pagina', 'pg']:
                if k in q:
                    key = k
                    break
            if key is None:
                # si no existe ningún parámetro de página, empezar en 2
                q['page'] = ['2']
            else:
                try:
                    cur = int(q.get(key, ['1'])[0])
                except Exception:
                    cur = 1
                q[key] = [str(cur + 1)]
            new_query = urlencode(q, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except Exception:
            return None
