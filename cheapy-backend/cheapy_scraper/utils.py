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