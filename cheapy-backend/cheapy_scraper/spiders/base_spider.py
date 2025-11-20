"""
Clase base para spiders de Cheapy.
Proporciona configuración común de headers y utilidades compartidas.
"""

from scrapy import Spider
from config import ACCEPT_LANGUAGE_BY_COUNTRY


class BaseCheapySpider(Spider):
    """
    Clase base para todos los spiders de Cheapy.

    Esta clase proporciona configuración común de headers HTTP, manejo de países
    y utilidades compartidas entre todos los spiders del proyecto.

    Attributes:
        country_code (str): Código del país para configuración regional
        accept_language (str): Header Accept-Language basado en el país
    """

    def __init__(self, country="US", *args, **kwargs):
        """
        Inicializa el spider con configuración específica del país.

        Args:
            country (str): Código del país (ej: 'US', 'AR', 'MX')
            *args: Argumentos adicionales para Spider
            **kwargs: Argumentos clave adicionales para Spider
        """
        super().__init__(*args, **kwargs)
        self.country_code = country.upper()

        # Configurar header Accept-Language basado en el país
        self.accept_language = ACCEPT_LANGUAGE_BY_COUNTRY.get(
            self.country_code,
            ACCEPT_LANGUAGE_BY_COUNTRY.get("DEFAULT", "en-US,en;q=0.9")
        )

    def get_default_headers(self):
        """
        Retorna los headers HTTP comunes para todas las requests.

        Returns:
            dict: Diccionario con headers HTTP optimizados
        """
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': self.accept_language,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }