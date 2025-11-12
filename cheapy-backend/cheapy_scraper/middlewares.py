# cheapy-backend/cheapy_scraper/middlewares.py

from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.http import Request # Se importa si se necesitara generar nuevos Requests, pero no es el caso actual

# Importa load_store_config, aunque el spider ya lo tiene, se mantiene la coherencia.
# En este middleware, se usará la 'spider.config' que ya está cargada.
from cheapy_scraper.utils.config_loader import load_store_config 

class PlaywrightStoreConfigMiddleware:
    """
    Middleware que lee las configuraciones de Playwright desde el JSON de la tienda
    (a través de spider.config) y las inyecta en la meta de la solicitud para scrapy-playwright.
    Esto permite controlar la navegación y los métodos de página de Playwright de forma dinámica.
    """

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        # Conecta este middleware a la señal spider_opened para que pueda inicializarse
        # y decidir si se activa o no para un spider específico.
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def spider_opened(self, spider):
        # Este middleware solo se activa si el spider es nuestro 'generic_spider'.
        # Si no lo es, se deshabilita para evitar interferir con otros spiders.
        if spider.name == 'generic_spider':
            spider.logger.info(f"PlaywrightStoreConfigMiddleware activado para {spider.name}")
        else:
            # Si no es el GenericSpider, este middleware no es necesario y se puede deshabilitar.
            # Esto evita que se ejecute innecesariamente para otros spiders que no usan este sistema.
            raise NotConfigured 

    def process_request(self, request, spider):
        # Asegúrate de que estamos procesando un GenericSpider
        if not spider.name == 'generic_spider':
            return None # Si no es GenericSpider, pasarlo al siguiente middleware

        # Si la configuración de la tienda NO requiere Playwright, simplemente pasamos la solicitud.
        # En este caso, el 'playwright' flag no debería estar en request.meta.
        if not spider.config.get('requires_playwright', False):
            # spider.logger.critical(f"DEBUG MIDDLEWARE: '{spider.store_name}' - No requiere Playwright. Saltando.")
            return None 

        # --- A partir de aquí, la tienda REQUIERE Playwright ---

        # Forzamos que 'playwright': True esté en la meta de la solicitud.
        # Esto es lo que le indica a scrapy-playwright que use el navegador.
        request.meta['playwright'] = True 

        # La configuración de la tienda ya está cargada en el objeto spider.
        store_config = spider.config 

        # 1. Inyectar playwright_page_goto_kwargs (parámetros para page.goto)
        # Esto incluye 'wait_until' y 'timeout' para la navegación inicial.
        if store_config.get('playwright_page_goto_kwargs'):
            request.meta['playwright_page_goto_kwargs'] = store_config['playwright_page_goto_kwargs']

        # 2. Inyectar playwright_page_methods (métodos a ejecutar DESPUÉS de page.goto)
        # Convertir las listas a tuplas, ya que scrapy-playwright las espera así.
        page_methods_raw = store_config.get('playwright_page_methods')
        if page_methods_raw:
            converted_page_methods = []
            for method_entry in page_methods_raw:
                if isinstance(method_entry, list):
                    converted_page_methods.append(tuple(method_entry)) # ¡Convertir a tupla!
                else: 
                    converted_page_methods.append(method_entry) # Ya debería ser una tupla o string
            request.meta['playwright_page_methods'] = converted_page_methods
        
        # Opcional: Log para depuración para ver la meta final inyectada.
        # spider.logger.critical(f"DEBUG MIDDLEWARE PLAYWRIGHT META: '{spider.store_name}' - Request meta final: {request.meta}")

        return None # Pasar la solicitud al siguiente middleware (que será Scrapy-Playwright)