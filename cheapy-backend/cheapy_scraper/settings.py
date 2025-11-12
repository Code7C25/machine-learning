# settings.py

BOT_NAME = "cheapy_scraper"

SPIDER_MODULES = ["cheapy_scraper.spiders"]
NEWSPIDER_MODULE = "cheapy_scraper.spiders"

# --- CONFIGURACIÓN ANTI-BLOQUEO ---

# 1. Descomenta y cambia el USER_AGENT por uno moderno y común.
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'

# 2. Respeta el robots.txt (buena práctica, aunque a veces es mejor ponerlo en False si te bloquea)
ROBOTSTXT_OBEY = False # Pongámoslo en False temporalmente para la depuración

# 3. Añade cabeceras por defecto que simulen un navegador real.
#    Esto es MUY efectivo contra bloqueos básicos.
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Sec-Ch-Ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

# -----------------------------------------------------------------------------
# MIDDLEWARES
# -----------------------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
   'scrapy.downloadermiddlewares.offsite.OffsiteMiddleware': 500, # Mantén los tuyos existentes
   'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware': 501,
   'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': 350, # Puedes ajustar prioridades
   'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 400,
   'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 500,
   'scrapy.downloadermiddlewares.retry.RetryMiddleware': 502,
   'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': 503,
   'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 590,
   'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
   'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
   'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
   'scrapy.downloadermiddlewares.stats.DownloaderStats': 800,
   
   # Activa tu nuevo middleware de Playwright
   'cheapy_scraper.middlewares.PlaywrightStoreConfigMiddleware': 540, # Se ejecuta después del UserAgent
}

# --- FIN CONFIGURACIÓN ANTI-BLOQUEO ---
# settings.py

# ... tus configs ...
USER_AGENT = '...'
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 1

#PLAYWRITE=============================================

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,  # Mantener en False para depuración visual
    "timeout": 60000,   
    # --- NUEVOS ARGUMENTOS PARA EL NAVEGADOR ---
    "args": [
        "--no-sandbox", # Necesario en algunos entornos Linux, no afecta Windows
        "--disable-setuid-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage", # Para contenedores
        "--incognito", # Iniciar en modo incógnito (limpio)
        "--disable-blink-features=AutomationControlled", # Intenta ocultar automatización JS
    ]
    # -------------------------------------------
}
PLAYWRIGHT_BROWSER_TYPE = "chromium" 
PLAYWRIGHT_USE_STEALTH = True # Mantener activo para intentar evitar la detección

RETRY_ENABLED = True 
DOWNLOADER_MIDDLEWARES = {
   # ...
   'cheapy_scraper.middlewares.PlaywrightStoreConfigMiddleware': 540, # ACTIVO
}

#======================================================

ITEM_PIPELINES = {
   # 1. Deduplicación (Se ejecuta primero, prioridad más baja)
    'cheapy_scraper.pipelines.DuplicatesPipeline': 100,
    
   # 2. Limpieza de Datos (Se ejecuta después de la deduplicación)
    'cheapy_scraper.pipelines.DataCleaningPipeline': 300, 
}
