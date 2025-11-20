# Scrapy settings for cheapy_scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "cheapy_scraper"

SPIDER_MODULES = ["cheapy_scraper.spiders"]
NEWSPIDER_MODULE = "cheapy_scraper.spiders"

# Configuración anti-bloqueo para scraping en producción
# Implementa simulación realista de navegador y limitación de tasa para evitar detección

# User agent realista simulando navegador Chrome moderno
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Cumplimiento de robots.txt deshabilitado para operaciones de scraping controladas
ROBOTSTXT_OBEY = False

# Limitación de tasa: 1 segundo de retraso entre solicitudes para evitar sobrecargar servidores
DOWNLOAD_DELAY = 1

# Timeout de solicitud: 15 segundos para evitar colgarse en sitios lentos/no responsivos
DOWNLOAD_TIMEOUT = 15

# Headers por defecto simulando una sesión de navegador real
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

# Middlewares de downloader para rotación de user agent
DOWNLOADER_MIDDLEWARES = {
   'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 500,
}

# Reactor AsyncIO para compatibilidad con librerías async modernas
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# Item processing pipelines with execution order
ITEM_PIPELINES = {
    # Validation pipeline: Ensures basic item integrity (90)
    'cheapy_scraper.pipelines.ValidationPipeline': 90,

    # Deduplication pipeline: Removes duplicate items by URL (100)
    'cheapy_scraper.pipelines.DuplicatesPipeline': 100,

    # Data cleaning pipeline: Normalizes and cleans extracted data (300)
    'cheapy_scraper.pipelines.DataCleaningPipeline': 300,
}

# Retry configuration for resilience against temporary failures
RETRY_ENABLED = True
RETRY_TIMES = 2
