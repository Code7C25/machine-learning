# cheapy-backend/cheapy_scraper/spiders/generic_spider.py

import scrapy
import asyncio 
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode 

from cheapy_scraper.items import ProductItem
from cheapy_scraper.utils.config_loader import load_store_config 

class GenericSpider(scrapy.Spider):
    """
    Un spider genérico que carga su configuración y selectores desde un archivo JSON.
    Permite raspar diferentes tiendas usando la misma base de código.
    """
    name = "generic_spider" 
    
    # Valores por defecto para el spider, pueden ser sobrescritos por la configuración de la tienda.
    MAX_PAGES = 2 
    ITEMS_PER_PAGE = 24 
    
    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
        'Referer': 'https://www.google.com/', 
    }

    def __init__(self, store_name="", query="", country="AR", **kwargs):
        super().__init__(**kwargs)
        if not store_name or not query:
            raise ValueError("Los argumentos 'store_name' y 'query' son obligatorios para GenericSpider.")
        
        self.store_name = store_name.lower()
        self.query = query
        self.country_code = country.upper()
        
        self.page_count = 0 
        self.logger.critical(f"DEBUG INIT: '{self.store_name}' - self.page_count inicializado a {self.page_count}, MAX_PAGES: {self.MAX_PAGES}")

        self.config = load_store_config(self.store_name)
        if not self.config:
            raise ValueError(f"Configuración NO ENCONTRADA para la tienda: '{self.store_name}'. Verifique el nombre del archivo JSON o su ubicación.")
        
        self.MAX_PAGES = self.config.get('max_pages', self.MAX_PAGES)
        self.ITEMS_PER_PAGE = self.config.get('items_per_page', self.ITEMS_PER_PAGE)
        
        domain = self.config['domain_map'].get(self.country_code, self.config['domain_map'].get('GLOBAL'))
        if not domain:
            raise ValueError(f"Dominio no encontrado para el país '{self.country_code}' en la configuración de '{self.store_name}'.")
        
        self.currency = self.config['currency_map'].get(self.country_code, self.config['currency_map'].get('GLOBAL', 'USD'))
        
        # --- CONSTRUCCIÓN DE LA URL DE INICIO (Centralizada en el JSON y ajustada para ML) ---
        query_space_separator = self.config.get('query_space_separator', '-')
        query_slug = self.query.replace(' ', query_space_separator) 
        
        base_url_template = self.config['search_base_url_template']
        
        if self.store_name == 'mercadolibre':
            final_ml_domain = self.config['domain_map'].get(self.country_code, self.config['domain_map'].get('GLOBAL'))
            if not final_ml_domain:
                raise ValueError(f"Dominio final de ML no encontrado para '{self.country_code}'")
            self.start_urls = [f"https://listado.mercadolibre.{final_ml_domain}/{query_slug}"]
        else:
            base_url = base_url_template.format(
                domain=domain, 
                query_slug=query_slug,
                page_num=1, 
                offset_start=0 
            )
            self.start_urls = [base_url]

        self.logger.critical(f"DEBUG INIT FINAL URL: '{self.store_name}' - start_urls final: {self.start_urls}")
        # --------------------------------------------------------

    # --- MÉTODO start() asíncrono (Punto de entrada para Scrapy 2.13+, gestiona Playwright) ---
    async def start(self):
        # Si la tienda REQUIERE Playwright, se gestionará la paginación dentro de una sola instancia de navegador.
        if self.config.get('requires_playwright', False):
            self.logger.info(f"'{self.store_name}' REQUIERE Playwright. Gestionando paginación con una única instancia.")
            
            # Prepara los meta_params para la primera solicitud de Playwright.
            # El middleware inyectará los playwright_page_goto_kwargs y playwright_page_methods
            playwright_meta_options = {
                'playwright': True,
                'store_name': self.store_name # Se usa en el middleware para cargar la config
            }
            
            # La primera solicitud Playwright usará parse_playwright_page como callback
            first_request = scrapy.Request(
                url=self.start_urls[0],
                headers=self.custom_headers,
                callback=self.parse_playwright_page, # <--- Callback específico para Playwright
                meta=playwright_meta_options.copy(),
                dont_filter=True # Importante para evitar que Scrapy filtre la primera URL si ya la vio.
            )
            yield first_request
        else:
            # Para tiendas que NO requieren Playwright, se usa el método start_requests tradicional.
            self.logger.critical(f"DEBUG START: '{self.store_name}' - No requiere Playwright. Usando start_requests().")
            for request in self.start_requests():
                yield request

    # --- MÉTODO start_requests() TRADICIONAL (Para spiders SIN Playwright) ---
    # Este método solo se llamará desde `start()` para casos no-Playwright.
    def start_requests(self):
        self.logger.critical(f"DEBUG START_REQUESTS: '{self.store_name}' - Enviando request normal para {self.start_urls[0]}")
        yield scrapy.Request(
            url=self.start_urls[0],
            headers=self.custom_headers,
            callback=self.parse # Callback al parse normal para scraping puro
        )

    def normalize_url(self, url):
        """Remueve fragmentos y query strings de seguimiento de las URLs para fines de deduplicación."""
        if not url:
            return url
        parsed = urlparse(url)
        return urlunparse(parsed._replace(query='', fragment=''))

    # --- MÉTODO parse() TRADICIONAL (Para spiders SIN Playwright) ---
    # Este método es el callback principal para solicitudes que NO USAN Playwright.
    def parse(self, response):
        self.page_count += 1
        self.logger.critical(f"DEBUG PARSE ENTRY: '{self.store_name}' - Procesando {response.url}, status: {response.status}")

        item_containers_selector = self.config['item_selectors'].get('container')
        if not item_containers_selector:
            self.logger.error(f"Configuración de '{self.store_name}' SIN 'item_selectors.container'. No se puede extraer nada de {response.url}.")
            return 

        item_containers = response.css(item_containers_selector)
        
        if not item_containers:
            self.logger.warning(f"No se encontraron ítems para '{self.store_name}' en {response.url} con selector: '{item_containers_selector}'.")
            filename = f'{self.store_name}_debug_page_{self.page_count}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            self.logger.critical(f"DEBUG: HTML de '{self.store_name}' guardado en {filename} para inspección manual.")
            
        for item_node in item_containers:
            product = self._extract_product_data(item_node, response) # Helper para extracción
            if product:
                yield product

        # --- Lógica de Paginación para Spiders SIN Playwright ---
        self.logger.critical(f"DEBUG PAGINATION CHECK_NORMAL: '{self.store_name}' - page_count={self.page_count}, MAX_PAGES={self.MAX_PAGES}. Condicion: {self.page_count < self.MAX_PAGES}")
        
        if self.page_count < self.MAX_PAGES:
            next_page_url = self._build_next_page_url(response.url)
            
            if next_page_url:
                self.logger.critical(f"DEBUG PAGINATION URL_NORMAL: '{self.store_name}' - Generado next_page_url: {next_page_url}")

                yield scrapy.Request(
                    url=next_page_url, 
                    headers=self.custom_headers,
                    callback=self.parse # Callback al parse normal
                )
            else:
                self.logger.error(f"No se pudo construir la URL para la próxima página de '{self.store_name}'. Verifique la configuración de paginación o el tipo de parámetro.")

    # --- NUEVO MÉTODO parse_playwright_page() para Playwright ---
    # Este método es el callback para solicitudes que SÍ USAN Playwright.
    async def parse_playwright_page(self, response):
        self.page_count += 1
        self.logger.critical(f"DEBUG PARSE_PLAYWRIGHT_PAGE ENTRY: '{self.store_name}' - Procesando {response.url}, status: {response.status}")

        item_containers_selector = self.config['item_selectors'].get('container')
        if not item_containers_selector:
            self.logger.error(f"Configuración de '{self.store_name}' SIN 'item_selectors.container'. No se puede extraer nada de {response.url}.")
            return 

        item_containers = response.css(item_containers_selector)
        
        if not item_containers:
            self.logger.warning(f"No se encontraron ítems para '{self.store_name}' en {response.url} con selector: '{item_containers_selector}'.")
            filename = f'{self.store_name}_debug_page_{self.page_count}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            self.logger.critical(f"DEBUG: HTML de '{self.store_name}' guardado en {filename} para inspección manual.")
            
        for item_node in item_containers:
            product = self._extract_product_data(item_node, response) # Helper para extracción
            if product:
                yield product

        # --- Lógica de Paginación CONTINUA EN LA MISMA PÁGINA (para Playwright) ---
        self.logger.critical(f"DEBUG PAGINATION CHECK_PLAYWRIGHT: '{self.store_name}' - page_count={self.page_count}, MAX_PAGES={self.MAX_PAGES}. Condicion: {self.page_count < self.MAX_PAGES}")
        
        if self.page_count < self.MAX_PAGES:
            next_page_url = self._build_next_page_url(response.url)
            
            if next_page_url:
                self.logger.critical(f"DEBUG PAGINATION URL_PLAYWRIGHT: '{self.store_name}' - Navegando a: {next_page_url}")
                
                # --- ACCESO A LA INSTANCIA DE PÁGINA DE PLAYWRIGHT A TRAVÉS DEL CONTEXTO ---
                playwright_context = response.meta.get("playwright_context")
                if not playwright_context:
                    self.logger.error(f"Error: No se encontró la instancia de contexto de Playwright en meta para {self.store_name}. No se puede paginar.")
                    return
                
                page = playwright_context.pages[0] # Obtener la primera página del contexto
                if not page:
                    self.logger.error(f"Error: No se encontró una página válida en el contexto de Playwright para {self.store_name}. No se puede paginar.")
                    return
                # -------------------------------------------------------------

                goto_kwargs = self.config.get('playwright_page_goto_kwargs', {})
                await page.goto(next_page_url, **goto_kwargs)
                
                # Ejecuta los playwright_page_methods definidos en el JSON para esperar el contenido
                for method_name, *args in self.config.get('playwright_page_methods', []):
                    if hasattr(page, method_name):
                        await getattr(page, method_name)(*args)
                    else:
                        self.logger.warning(f"Playwright: Método '{method_name}' no encontrado en la página para '{self.store_name}'.")

                # Re-scrapea la nueva página usando el mismo callback.
                # Es CRÍTICO pasar la meta original (que contiene el contexto) para la próxima llamada.
                yield response.request.replace(
                    url=next_page_url, 
                    callback=self.parse_playwright_page,
                    meta=response.meta.copy(), # Copiar toda la meta (incluyendo 'playwright_context')
                    dont_filter=True 
                )
            else:
                self.logger.error(f"No se pudo construir la URL para la próxima página de '{self.store_name}'. Verifique la configuración de paginación o el tipo de parámetro.")

    # --- MÉTODO HELPER para construir la URL de la siguiente página ---
    def _build_next_page_url(self, current_url: str) -> str:
        pagination_param = self.config.get('pagination_param')
        items_per_page = self.config.get('items_per_page', self.ITEMS_PER_PAGE) 
        
        if not pagination_param:
            return None
            
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)
        
        next_page_url = None

        if pagination_param == "_Desde": # Para sitios que usan offset (ej. MercadoLibre)
            current_offset_str = query_params.get(pagination_param, ['0'])[0]
            try:
                current_offset = int(current_offset_str)
            except ValueError:
                current_offset = 0 
            
            new_offset = current_offset + items_per_page
            query_params[pagination_param] = [str(new_offset)]

            # Para MercadoLibre, la lógica de 'q=' se omitió para replicar tu spider original.
            # if self.store_name == 'mercadolibre' and 'q' not in query_params:
            #     query_params['q'] = [self.query.replace(' ', self.config.get('query_space_separator', '-'))]
            
            next_page_url = urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True), fragment=''))
        
        elif pagination_param == "page": # Para sitios que usan número de página (ej. Fravega, AliExpress, Megatone)
            current_page_num = 1
            if query_params.get(pagination_param):
                try:
                    current_page_num = int(query_params.get(pagination_param)[0])
                except ValueError:
                    pass
            
            next_page_num = current_page_num + 1
            query_params[pagination_param] = [str(next_page_num)]

            search_query_param_name = self.config.get('search_query_param_name')
            if search_query_param_name and search_query_param_name not in query_params:
                query_params[search_query_param_name] = [self.query.replace(' ', self.config.get('query_space_separator', '+'))]
            
            next_page_url = urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True), fragment=''))
        
        return next_page_url
    
    # --- MÉTODO HELPER para extraer datos de producto (unificado) ---
    def _extract_product_data(self, item_node, response):
        product = ProductItem()
        
        title_selector = self.config['item_selectors'].get('title')
        url_selector = self.config['item_selectors'].get('url')
        
        title = item_node.css(title_selector).get() if title_selector else None
        url = item_node.css(url_selector).get() if url_selector else None
        
        if url and not url.startswith('http'):
            url = response.urljoin(url)
        
        if not title or not url:
            self.logger.debug(f"Saltando ítem incompleto en '{self.store_name}'. Título: '{title}', URL: '{url}'")
            return None

        product['title'] = title.strip() if title else None
        product['url'] = self.normalize_url(url)
        product['source'] = self.config['name']
        product['currency_code'] = self.currency
        product['country_code'] = self.country_code

        image_url_selector = self.config['item_selectors'].get('image_url')
        product['image_url'] = item_node.css(image_url_selector).get() if image_url_selector else None

        price_full_str = None
        price_current_selector = self.config['item_selectors'].get('price_current')
        price_symbol_selector = self.config['item_selectors'].get('price_symbol')
        price_fraction_selector = self.config['item_selectors'].get('price_fraction')
        price_fraction_discount_selector = self.config['item_selectors'].get('price_fraction_discount')
        price_fraction_normal_selector = self.config['item_selectors'].get('price_fraction_normal')

        if price_current_selector:
            price_full_str = item_node.css(price_current_selector).get()
        elif price_symbol_selector or price_fraction_selector or price_fraction_discount_selector or price_fraction_normal_selector:
            price_symbol = item_node.css(price_symbol_selector).get() if price_symbol_selector else None
            price_fraction = item_node.css(price_fraction_selector).get() if price_fraction_selector else None
            price_fraction_discount = item_node.css(price_fraction_discount_selector).get() if price_fraction_discount_selector else None
            price_fraction_normal = item_node.css(price_fraction_normal_selector).get() if price_fraction_normal_selector else None
            
            final_price_fraction = price_fraction_discount or price_fraction_normal or price_fraction
            price_full_str = f"{price_symbol or ''}{final_price_fraction or ''}" if final_price_fraction else None
        
        product['price'] = price_full_str.strip() if price_full_str else None

        rating_str_selector = self.config['item_selectors'].get('rating_str')
        reviews_count_str_selector = self.config['item_selectors'].get('reviews_count_str')
        
        product['rating_str'] = item_node.css(rating_str_selector).get() if rating_str_selector else None
        product['reviews_count_str'] = item_node.css(reviews_count_str_selector).get() if reviews_count_str_selector else None
        
        return product