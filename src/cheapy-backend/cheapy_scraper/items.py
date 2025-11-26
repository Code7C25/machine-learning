import scrapy

class ProductItem(scrapy.Item):
    """
    Item de Scrapy que define la estructura para los datos de productos extraídos de sitios de comercio electrónico.
    Incluye campos crudos de los spiders y campos procesados de los pipelines.
    """
    title = scrapy.Field()
    url = scrapy.Field()
    image_url = scrapy.Field()
    source = scrapy.Field()
    price = scrapy.Field()
    rating_str = scrapy.Field()
    reviews_count_str = scrapy.Field()
    reviews_count_raw = scrapy.Field()
    currency_code = scrapy.Field()
    country_code = scrapy.Field()

    price_numeric = scrapy.Field()
    currency = scrapy.Field()
    rating = scrapy.Field()
    reviews_count = scrapy.Field()
    price_display = scrapy.Field()
    price_before = scrapy.Field()
    price_before_numeric = scrapy.Field()
    is_discounted = scrapy.Field()
    on_sale = scrapy.Field()
    discount_percent = scrapy.Field()