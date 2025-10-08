# cheapy-backend/config.py

# Diccionario de dominios de Mercado Libre por país
MERCADOLIBRE_DOMAINS = {
    'AR': 'com.ar', 'BO': 'com.bo', 'BR': 'com.br', 'CL': 'cl',
    'CO': 'com.co', 'CR': 'co.cr', 'DO': 'com.do', 'EC': 'com.ec',
    'GT': 'com.gt', 'HN': 'com.hn', 'MX': 'com.mx', 'NI': 'com.ni',
    'PA': 'com.pa', 'PY': 'com.py', 'PE': 'com.pe', 'SV': 'com.sv',
    'UY': 'com.uy', 'VE': 'co.ve'
}

# Diccionario de monedas por país (puedes expandir esto)
COUNTRY_CURRENCIES = {
    'AR': 'ARS', 'CL': 'CLP', 'CO': 'COP', 'MX': 'MXN', 'BR': 'BRL', 'PE': 'PEN', 'UY': 'UYU'
    # Añadir más según sea necesario
}