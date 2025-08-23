import scrapy


class ProductItem(scrapy.Item):
    title = scrapy.Field()
    price_raw = scrapy.Field()
    price_num = scrapy.Field()
    link = scrapy.Field()
    image = scrapy.Field()
    domain = scrapy.Field()
    query = scrapy.Field()
