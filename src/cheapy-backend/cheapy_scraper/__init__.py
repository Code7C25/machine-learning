"""
Módulo principal del scraper Cheapy.

Este paquete contiene toda la lógica de scraping para múltiples plataformas
de e-commerce, incluyendo spiders especializados y utilidades compartidas.
"""

# Imports centralizados para facilitar el uso del módulo
from .utils import get_country_headers

__all__ = ['get_country_headers']