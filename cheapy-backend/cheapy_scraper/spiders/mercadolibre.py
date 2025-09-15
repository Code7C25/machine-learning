import scrapy
import re

class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"
    MAX_PAGES = 4  # Límite de páginas a scrapear
    ITEMS_PER_PAGE = 50

    # Headers para simular un navegador real
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }

    def __init__(self, query="", **kwargs):
        super().__init__(**kwargs)
        if not query:
            raise ValueError("El argumento 'query' es obligatorio. Uso: scrapy crawl mercadolibre -a query='tu busqueda'")
        self.query = query
        # La URL de inicio se construye una sola vez
        base_url = f"https://listado.mercadolibre.com.ar/{self.query.replace(' ', '-')}"
        print(f"[SPIDER] URL inicial: {base_url}")
        self.start_urls = [base_url]
        self.page_count = 0

    def parse(self, response):
        self.page_count += 1
        msg = f"[SPIDER] Parseando página {self.page_count}/{self.MAX_PAGES} - {response.url}"
        print(msg); self.logger.info(msg)

        # --- Extraer productos ---
        items = response.css('li.ui-search-layout__item')
        print(f"[SPIDER] {len(items)} productos detectados en la página {self.page_count}")

        item_count = 0
        for item in items:
            title = item.css('h2.ui-search-item__title::text').get() or \
                    item.css('h3.poly-component__title-wrapper a.poly-component__title::text').get()

            url = item.css('a.ui-search-link::attr(href)').get() or \
                  item.css('a.poly-component__title::attr(href)').get()

            if not title or not url:
                continue

            price_fraction = item.css('span.andes-money-amount__fraction::text').get()
            price_symbol = item.css('span.andes-money-amount__currency-symbol::text').get()
            
            rating_str = item.css('.ui-search-reviews__rating-number::text').get() or \
                         item.css('span.poly-reviews__rating::text').get()
            
            reviews_count_str = item.css('.ui-search-reviews__amount::text').get() or \
                                item.css('span.poly-reviews__total::text').get()

            image_url = item.css('.ui-search-result__image-container img::attr(data-src)').get() or \
            item.css('.ui-search-result__image-container img::attr(src)').get() or \
            item.css('.poly-card__portada img::attr(data-src)').get() or \
            item.css('.poly-card__portada img::attr(src)').get()
                        
            price = "Sin precio"
            if price_fraction:
                price = f"{(price_symbol or '$').strip()} {price_fraction.strip().replace('.', '')}"
            
            rating = 0.0
            if rating_str:
                try:
                    rating = float(rating_str.replace(',', '.'))
                except:
                    rating = 0.0

            reviews_count = 0
            if reviews_count_str:
                numbers = re.findall(r'\d+', reviews_count_str)
                if numbers:
                    reviews_count = int(numbers[0])
            
            item_count += 1
            yield {
                "title": title.strip(),
                "price": price,
                "url": response.urljoin(url),
                "image_url": image_url,
                "source": "Mercado Libre",
                "reliability_score": round(rating),
                "reviews_count": reviews_count
            }
        
        print(f"[RESUMEN SIMPLE] Página {self.page_count}: {item_count} productos extraídos.")

        # --- Lógica de Paginación (Usando los selectores del usuario) ---
        if self.page_count < self.MAX_PAGES:
            # Usamos el selector exacto que proporcionaste
            next_page_selector = 'li.andes-pagination__button--next a.andes-pagination__link::attr(href)'
            next_page_url = response.css(next_page_selector).get()
            
            if next_page_url:
                print(f"[SPIDER] → Encontrado botón 'Siguiente'. Navegando a la página {self.page_count + 1}")
                self.logger.info(f"Siguiendo a la página: {next_page_url}")
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse,
                    errback=self.handle_error
                )
            else:
                print("[SPIDER] ❌ No se encontró el botón 'Siguiente'. Fin de la paginación.")
                self.logger.warning("No se encontró el enlace a la siguiente página.")

    def handle_error(self, failure):
        print(f"[SPIDER] ❌ Error en la petición: {repr(failure)}")
        self.logger.error(f"FALLO en la petición: {repr(failure)}")

