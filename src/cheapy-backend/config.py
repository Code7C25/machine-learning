COUNTRY_CURRENCIES = {
    'AR': 'ARS', 'MX': 'MXN', 'CO': 'COP', 'CL': 'CLP', 'BR': 'BRL', 'UY': 'UYU',
    'PE': 'PEN', 'CR': 'CRC', 'GT': 'GTQ', 'HN': 'HNL', 'NI': 'NIO', 'PA': 'PAB',
    'SV': 'USD', 'DO': 'DOP', 'BO': 'BOB', 'PY': 'PYG', 'VE': 'VES', 'EC': 'USD',
    'CU': 'CUP', 'US': 'USD', 'CA': 'CAD', 'ES': 'EUR', 'DE': 'EUR', 'FR': 'EUR',
    'IT': 'EUR', 'GB': 'GBP', 'JP': 'JPY', 'CN': 'CNY', 'AU': 'AUD', 'IN': 'INR',
}

ACCEPT_LANGUAGE_BY_COUNTRY = {
    'DEFAULT': 'en-US,en;q=0.9',
    'US': 'en-US,en;q=0.9',
    'CA': 'en-CA,en;q=0.8,fr-CA;q=0.6',
    'GB': 'en-GB,en;q=0.9',
    'ES': 'es-ES,es;q=0.9,en;q=0.6',
    'AR': 'es-AR,es;q=0.9,en;q=0.6',
    'MX': 'es-MX,es;q=0.9,en;q=0.6',
    'BR': 'pt-BR,pt;q=0.9,en;q=0.6',
    'DE': 'de-DE,de;q=0.9,en;q=0.6',
    'FR': 'fr-FR,fr;q=0.9,en;q=0.6',
    'IT': 'it-IT,it;q=0.9,en;q=0.6',
    'JP': 'ja-JP,ja;q=0.9,en;q=0.6',
}

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
    'BR': 'pt.aliexpress.com',
    'US': 'www.aliexpress.com',
}

COUNTRY_TO_SPIDERS = {
    'AR': ['mercadolibre','fravega'],
    'CO': ['mercadolibre'],
    'CL': ['mercadolibre'],
    'MX': ['mercadolibre', 'amazon'],
    'BR': ['mercadolibre', 'amazon', 'aliexpress'],
    'US': ['amazon', 'ebay'],
    'CA': ['amazon', 'ebay'],
    'ES': ['amazon', 'ebay', 'aliexpress'],
}