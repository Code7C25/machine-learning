import scrapy
from pathlib import Path

class EbaySpider(scrapy.Spider):
    """
    Spider para extraer datos de productos de eBay (sitio internacional).
    """
    name = "ebay"

    def __init__(self, query="", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.start_url = f"https://www.ebay.com/sch/i.html?_nkw={self.query.replace(' ', '+')}"
    
    async def start(self):
        """
        Método de inicio del spider. Se ejecuta una vez al principio.
        """
        self.logger.info(f"EbaySpider: Enviando petición a {self.start_url}")
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse,
            errback=self.handle_error
        )

    def parse(self, response):
        """
        Procesa la respuesta exitosa de eBay y extrae los datos.
        """
        self.logger.info(f"EbaySpider: Respuesta recibida con éxito (Status: {response.status})")

        # Busca todos los contenedores de productos en la página
        items = response.css('li.s-item')
        self.logger.info(f"EbaySpider: Encontrados {len(items)} items de producto.")
        
        item_count = 0
        # Itera sobre los primeros 10 resultados, omitiendo el primero que a veces es un anuncio
        for item in items[1:11]: 
            title = item.css('div.s-item__title span[role=heading]::text').get()
            price = item.css('span.s-item__price::text').get()
            url = item.css('a.s-item__link::attr(href)').get()

            # Valida que todos los datos necesarios hayan sido extraídos
            if title and price and url:
                item_count += 1
                yield {
                    "title": title.strip(),
                    "price": price.strip(),
                    "url": url,
                    "source": "eBay"
                }
            else:
                self.logger.debug(f"Item omitido por falta de datos. Title: {title}, Price: {price}, URL: {url}")

        if item_count == 0:
            self.logger.warning("EbaySpider: No se pudo extraer ningún producto. El layout de la página puede haber cambiado.")
        else:
            self.logger.info(f"EbaySpider: Extraídos {item_count} productos.")

    def handle_error(self, failure):
        """
        Maneja cualquier error que ocurra durante la petición HTTP.
        """
        self.logger.error(f"EbaySpider: FALLO en la petición. Razón: {repr(failure)}")