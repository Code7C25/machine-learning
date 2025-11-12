# Tests simples para helpers de paginación (sin requests reales)
import sys
sys.path.insert(0, r"c:\Users\Usuario\OneDrive\Desktop\proyecto IA\Proyecto2\machine-learning\cheapy-backend")

from cheapy_scraper.spiders.mercadolibre import MercadoLibreSpider
from cheapy_scraper.spiders.fravega import FravegaSpider


def test_meli_compute_next():
    spider = MercadoLibreSpider(query="electronica-audio-video/televisores/tv")

    # Caso 1: URL inicial sin _Desde_
    url1 = "https://listado.mercadolibre.com.ar/electronica-audio-video/televisores/tv"
    next1 = spider._compute_next_meli_url(url1)
    assert next1.endswith("tv_Desde_51_NoIndex_True"), next1

    # Caso 2: URL con _Desde_51 -> _Desde_101
    url2 = "https://listado.mercadolibre.com.ar/electronica-audio-video/televisores/tv_Desde_51_NoIndex_True"
    next2 = spider._compute_next_meli_url(url2)
    assert "_Desde_101" in next2, next2


def test_fravega_compute_next():
    spider = FravegaSpider(query="tv")

    # Caso 1: página con ?page=2 -> page=3
    url1 = "https://www.fravega.com/l/tv-y-video/tv/?page=2"
    next1 = spider._compute_next_fravega_url(url1)
    assert next1.endswith("?page=3"), next1

    # Caso 2: sin page -> page=2
    url2 = "https://www.fravega.com/l/tv-y-video/tv/"
    next2 = spider._compute_next_fravega_url(url2)
    assert next2.endswith("?page=2"), next2

if __name__ == "__main__":
    # Ejecutar tests manualmente
    try:
        test_meli_compute_next()
        print("test_meli_compute_next: OK")
    except AssertionError as e:
        print("test_meli_compute_next: FAIL:", e)

    try:
        test_fravega_compute_next()
        print("test_fravega_compute_next: OK")
    except AssertionError as e:
        print("test_fravega_compute_next: FAIL:", e)
