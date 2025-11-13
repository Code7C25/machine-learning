# settings.py

BOT_NAME = "cheapy_scraper"

SPIDER_MODULES = ["cheapy_scraper.spiders"]
NEWSPIDER_MODULE = "cheapy_scraper.spiders"

# --- CONFIGURACIÓN ANTI-BLOQUEO ---

# 1) User-Agent realista y único (evitar overrides duplicados)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 2) Robots y ritmo de descarga
ROBOTSTXT_OBEY = False  # Desactivado durante scraping controlado
DOWNLOAD_DELAY = 1      # 1 segundo entre requests
DOWNLOAD_TIMEOUT = 15   # Timeout por request para evitar bloqueos largos

# 3) Cabeceras por defecto similares a un navegador
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Sec-Ch-Ua': '"Google Chrome";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

# 4) Middleware de User-Agent
DOWNLOADER_MIDDLEWARES = {
   'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 500,
}

# --- FIN CONFIGURACIÓN ANTI-BLOQUEO ---

# Nota: Para forzar que SOLO ciertos spiders usen Playwright,
# NO configuramos aquí los DOWNLOAD_HANDLERS de Playwright a nivel global.
# En su lugar, cada spider que necesite Playwright (p. ej., Megatone)
# define custom_settings con esos handlers.

# Mantener reactor AsyncIO es seguro aún sin usar Playwright globalmente
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

ITEM_PIPELINES = {
    # 0. Validación básica (dropear sin imagen/url)
    'cheapy_scraper.pipelines.ValidationPipeline': 90,

    # 1. Deduplicación (Se ejecuta después de validación)
    'cheapy_scraper.pipelines.DuplicatesPipeline': 100,
    
   # 2. Limpieza de Datos (Se ejecuta después de la deduplicación)
    'cheapy_scraper.pipelines.DataCleaningPipeline': 300, 
}

# Reintentos básicos (resiliencia)
RETRY_ENABLED = True
RETRY_TIMES = 2
