# cheapy-backend/config.py

# Mapeo genérico de códigos de país a sus monedas oficiales
COUNTRY_CURRENCIES = {
    'AR': 'ARS', 'MX': 'MXN', 'CO': 'COP', 'CL': 'CLP', 'BR': 'BRL', 'UY': 'UYU',
    'PE': 'PEN', 'CR': 'CRC', 'GT': 'GTQ', 'HN': 'HNL', 'NI': 'NIO', 'PA': 'PAB',
    'SV': 'USD', 'DO': 'DOP', 'BO': 'BOB', 'PY': 'PYG', 'VE': 'VES', 'EC': 'USD',
    'CU': 'CUP', 'US': 'USD', 'CA': 'CAD', 'ES': 'EUR', 'DE': 'EUR', 'FR': 'EUR',
    'IT': 'EUR', 'GB': 'GBP', 'JP': 'JPY', 'CN': 'CNY', 'AU': 'AUD', 'IN': 'INR',
}

# --- Configuraciones por Tienda ---

MERCADOLIBRE_DOMAINS = {
    'AR': 'com.ar', 'MX': 'com.mx', 'CO': 'com.co', 'CL': 'cl', 'BR': 'com.br',
    'UY': 'com.uy', 'PE': 'com.pe', 'CR': 'co.cr', 'GT': 'com.gt', 'HN': 'com.hn',
    'NI': 'com.ni', 'PA': 'com.pa', 'SV': 'com.sv', 'DO': 'com.do', 'BO': 'com.bo',
    'PY': 'com.py', 'VE': 'com.ve', 'EC': 'com.ec', 'CU': 'com.cu',
}

AMAZON_DOMAINS = {
    'US': 'com', 'CA': 'ca', 'MX': 'com.mx', 'BR': 'com.br', 'ES': 'es', 'GB': 'co.uk',
    'DE': 'de', 'FR': 'fr', 'IT': 'it', 'JP': 'co.jp', 'AU': 'com.au', 'CN': 'cn',
}

EBAY_DOMAINS = {
    'US': 'com', 'CA': 'ca', 'AU': 'com.au', 'GB': 'co.uk', 'DE': 'de', 'FR': 'fr',
    'ES': 'es', 'IT': 'it',
}

ALIEXPRESS_DOMAINS = {
    'ES': 'es.aliexpress.com',
    'FR': 'fr.aliexpress.com',
    'DE': 'de.aliexpress.com',
    'IT': 'it.aliexpress.com',
    'BR': 'pt.aliexpress.com', # Para Brasil, es el subdominio de portugués
    'US': 'www.aliexpress.com', # Para EEUU y por defecto, es www.
}

# --- Cerebro del Despachador ---
# Mapeo de país a una lista de spiders que se ejecutarán para ese país.
COUNTRY_TO_SPIDERS = {
    # LATAM
    'AR': ['mercadolibre','fravega'],
    'CO': ['mercadolibre'],
    'CL': ['mercadolibre'],
    
    # Países con Múltiples Tiendas
    'MX': ['mercadolibre', 'amazon'],
    'BR': ['mercadolibre', 'amazon', 'aliexpress'],
    'US': ['amazon', 'ebay', 'aliexpress'],
    'CA': ['amazon', 'ebay'],
    'ES': ['amazon', 'ebay', 'aliexpress'],
    
    # Por defecto, si un país no está aquí, no se ejecutará ningún spider.
}