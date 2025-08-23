import scrapy
from scraper.items import ProductItem
import re


class MercadoLibreSpider(scrapy.Spider):
    name = "mercadolibre"
    allowed_domains = ["mercadolibre.com.ar", "listado.mercadolibre.com.ar"]

    def __init__(self, query=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not query:
            raise ValueError("Se requiere el argumento query, usa -a query='tu búsqueda'")
        self.query = query
        self.start_urls = ["https://listado.mercadolibre.com.ar/{query.replace(' ', '-')}"]

    def parse(self, response):
        cards = response.css('.ui-search-layout__item')
        for c in cards[:12]:
            title = c.css('.ui-search-item__title::text').get()
            price_raw = c.css('.andes-money-amount__fraction::text').get()
            img = c.css('.ui-search-result-image__element::attr(data-src)').get() or c.css('.ui-search-result-image__element::attr(src)').get()
            link = c.css('a.ui-search-link::attr(href)').get()
            price_num = None
            if price_raw:
                try:
                    price_num = float(price_raw.replace('.', '').replace(',', '.'))
                except:
                    price_num = None
            if title and link:
                item = ProductItem(
                    title=title.strip(),
                    price_raw=price_raw,
                    price_num=price_num,
                    image=img,
                    link=link,
                    domain='mercadolibre.com.ar',
                    query=self.query
                )
                yield item
