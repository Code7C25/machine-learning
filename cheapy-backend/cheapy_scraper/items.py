# cheapy-backend/cheapy_scraper/items.py
import scrapy

class ProductItem(scrapy.Item):
    # --- Datos extraídos por el Spider ---
    title = scrapy.Field()
    url = scrapy.Field()
    image_url = scrapy.Field()
    source = scrapy.Field()
    price = scrapy.Field()           # Precio crudo (ej: "$ 1.500.000")
    rating_str = scrapy.Field()      # Rating crudo (ej: "4.5")
    reviews_count_str = scrapy.Field() # Reviews crudo (ej: "(150)")
    currency_code = scrapy.Field()   # Código de moneda pasado por el spider (ej: "ARS")

    # --- Datos generados por el Pipeline ---
    price_numeric = scrapy.Field()   # Precio limpio (ej: 1500000.0)
    currency = scrapy.Field()        # Moneda limpia (ej: "ARS")
    rating = scrapy.Field()          # Rating limpio (ej: 4.5)
    reviews_count = scrapy.Field()   # Reviews limpio (ej: 150)