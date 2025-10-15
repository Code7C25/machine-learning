import scrapy
from config import EBAY_DOMAINS, COUNTRY_CURRENCIES

class EbaySpider(scrapy.Spider):
    name = "ebay"

    def __init__(self, query="", country="US", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.country_code = country.upper()
        domain = EBAY_DOMAINS.get(self.country_code, EBAY_DOMAINS['US'])
        self.currency = COUNTRY_CURRENCIES.get(self.country_code, 'USD')
        self.start_urls = [f"https://www.ebay.{domain}/sch/i.html?_nkw={self.query.replace(' ', '+')}"]
        self.logger.info(f"Iniciando eBay spider para País: {self.country_code}, Dominio: {domain}")

    def parse(self, response):
        products = response.css('li.s-item')
        for product in products:
            yield {
                'title': product.css('.s-item__title::text').get(),
                'url': product.css('a.s-item__link::attr(href)').get(),
                'image_url': product.css('.s-item__image-wrapper img::attr(src)').get(),
                'source': self.name,
                'price': product.css('.s-item__price::text').get(),
                'rating_str': None, # eBay no muestra rating en la lista de búsqueda
                'reviews_count_str': product.css('.s-item__reviews-count span::text').get(),
                'currency_code': self.currency,
                'country_code': self.country_code,
            }