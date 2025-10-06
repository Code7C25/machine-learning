# Este archivo centraliza la información compartida entre diferentes partes de la aplicación.

# Mapeo de códigos de país a sus monedas oficiales (ISO 4217)
# Esta lista es genérica y puede ser usada por CUALQUIER spider.
COUNTRY_CURRENCIES = {
    'AR': 'ARS', 'MX': 'MXN', 'CO': 'COP', 'CL': 'CLP', 'BR': 'BRL',
    'UY': 'UYU', 'PE': 'PEN', 'CR': 'CRC', 'GT': 'GTQ', 'HN': 'HNL',
    'NI': 'NIO', 'PA': 'PAB', 'SV': 'USD', 'DO': 'DOP', 'BO': 'BOB',
    'PY': 'PYG', 'VE': 'VES', 'EC': 'USD', 'CU': 'CUP',
    
    # Países para futuros spiders
    'US': 'USD', # Estados Unidos
    'CA': 'CAD', # Canadá
    'ES': 'EUR', # España
    'DE': 'EUR', # Alemania
    'FR': 'EUR', # Francia
    'IT': 'EUR', # Italia
    'GB': 'GBP', # Reino Unido
    'JP': 'JPY', # Japón
    'CN': 'CNY', # China
    'AU': 'AUD', # Australia
    'IN': 'INR', # India
}

# Mapeo específico para el spider de Mercado Libre
# Contiene el dominio específico de la tienda para cada país.
MERCADOLIBRE_DOMAINS = {
    'AR': 'com.ar', 'MX': 'com.mx', 'CO': 'com.co', 'CL': 'cl', 'BR': 'com.br',
    'UY': 'com.uy', 'PE': 'com.pe', 'CR': 'co.cr', 'GT': 'com.gt', 'HN': 'com.hn',
    'NI': 'com.ni', 'PA': 'com.pa', 'SV': 'com.sv', 'DO': 'com.do', 'BO': 'com.bo',
    'PY': 'com.py', 'VE': 'com.ve', 'EC': 'com.ec', 'CU': 'com.cu',
}

# Podrías añadir configuraciones para futuros spiders aquí
# AMAZON_DOMAINS = {
#     'US': 'com', 'CA': 'ca', 'MX': 'com.mx', 'ES': 'es', 'DE': 'de', 
#     'FR': 'fr', 'IT': 'it', 'GB': 'co.uk', 'JP': 'co.jp', 'CN': 'cn',
#     'AU': 'com.au', 'IN': 'in', 'BR': 'com.br',
# }