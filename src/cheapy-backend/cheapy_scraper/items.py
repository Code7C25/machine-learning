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
    reviews_count_raw = scrapy.Field() # Campo crudo preservado para debugging (ej: '+10mil', '(10000000)')
    currency_code = scrapy.Field()   # Código de moneda pasado por el spider (ej: "ARS")
    country_code = scrapy.Field()

    # --- Datos generados por el Pipeline ---
    price_numeric = scrapy.Field()   # Precio limpio (ej: 1500000.0)
    currency = scrapy.Field()        # Moneda limpia (ej: "ARS")
    rating = scrapy.Field()          # Rating limpio (ej: 4.5)
    reviews_count = scrapy.Field()   # Reviews limpio (ej: 150)
    price_display = scrapy.Field()   # Precio crudo para mostrar en frontend (ej: "$ 1.500.000")
    # --- Campos para descuentos y precio anterior ---
    price_before = scrapy.Field()        # Precio anterior crudo (ej: "$ 1.800.000")
    price_before_numeric = scrapy.Field()# Precio anterior numérico (ej: 1800000.0)
    # Señal genérica enviada por los spiders para indicar que el ítem está en oferta
    is_discounted = scrapy.Field()
    on_sale = scrapy.Field()             # Booleano si está en oferta
    discount_percent = scrapy.Field()    # Porcentaje de descuento calculado (ej: 15.5)