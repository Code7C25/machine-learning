"""
Utilidades comunes para el scraper Cheapy.

Este módulo contiene funciones auxiliares compartidas entre diferentes
componentes del sistema de scraping.
"""


def get_country_headers(country_code: str) -> dict:
    """
    Retorna headers HTTP optimizados para un país específico.

    Esta función centraliza la configuración de headers HTTP que dependen
    del país, asegurando consistencia entre todos los spiders.

    Args:
        country_code (str): Código del país (ej: 'US', 'AR', 'MX')

    Returns:
        dict: Diccionario con headers HTTP configurados para el país

    Example:
        >>> headers = get_country_headers('AR')
        >>> print(headers['Accept-Language'])
        es-AR,es;q=0.9,en;q=0.8
    """
    from config import ACCEPT_LANGUAGE_BY_COUNTRY

    # Obtener el header Accept-Language para el país especificado
    accept_lang = ACCEPT_LANGUAGE_BY_COUNTRY.get(
        country_code.upper(),
        ACCEPT_LANGUAGE_BY_COUNTRY.get("DEFAULT", "en-US,en;q=0.9")
    )

    # Retornar headers completos y optimizados
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': accept_lang,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


def parse_price(price_str: str, country_code: str = 'US') -> float:
    """
    Convierte una cadena de precio a un valor numérico float.

    Esta función centraliza el parsing de precios de diferentes formatos
    monetarios, manejando separadores decimales y de miles según el país.
    Elimina símbolos de moneda y caracteres no numéricos.

    Args:
        price_str (str): Cadena de precio (ej: "$1.234,56", "USD 1,234.56")
        country_code (str): Código del país para formato específico

    Returns:
        float: Valor numérico del precio, o 0.0 si no se puede parsear

    Examples:
        >>> parse_price("$1.234,56", "AR")  # Argentina
        1234.56
        >>> parse_price("USD 1,234.56", "US")  # Estados Unidos
        1234.56
        >>> parse_price("€ 1.234,56", "DE")  # Alemania
        1234.56
    """
    if not price_str or not isinstance(price_str, str):
        return 0.0

    try:
        # Eliminar símbolos de moneda comunes y espacios extra
        cleaned = price_str.strip()
        cleaned = cleaned.replace('$', '').replace('€', '').replace('£', '').replace('¥', '')
        cleaned = cleaned.replace('USD', '').replace('EUR', '').replace('ARS', '').replace('BRL', '')
        cleaned = cleaned.replace('MXN', '').replace('COP', '').replace('PEN', '').replace('CLP', '')

        # Manejar formatos por país
        if country_code.upper() in ['AR', 'BR', 'DE', 'ES', 'FR', 'IT', 'PT']:
            # Formato europeo: 1.234,56 (punto = miles, coma = decimal)
            cleaned = cleaned.replace('.', '')  # Remover separador de miles
            cleaned = cleaned.replace(',', '.')  # Convertir coma a punto decimal
        else:
            # Formato estadounidense: 1,234.56 (coma = miles, punto = decimal)
            cleaned = cleaned.replace(',', '')  # Remover separador de miles

        # Convertir a float
        return float(cleaned)

    except (ValueError, AttributeError):
        # Si no se puede convertir, retornar 0
        return 0.0