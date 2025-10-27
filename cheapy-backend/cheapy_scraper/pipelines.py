import re
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem # ¡Necesitas importar esto!

# ===============================================
# NUEVA PIPELINE DE DEDUPLICACIÓN
# ===============================================

class DuplicatesPipeline:
    """
    Elimina ítems duplicados basándose en la URL normalizada del producto.
    """
    def __init__(self):
        # Usamos un conjunto (set) para almacenar las URLs vistas en esta corrida.
        self.urls_seen = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get('url') 
        
        # Es crucial que la URL haya sido normalizada en el Spider (Paso 3)
        if not url:
            # Si no hay URL, el ítem no puede ser rastreado, lo descartamos
            raise DropItem("Item sin URL detectado, descartando.")

        if url in self.urls_seen:
            # Si la URL ya fue vista, descartamos el ítem duplicado.
            spider.logger.debug(f"Descartando ítem duplicado: {adapter['title']} - {url}")
            raise DropItem(f"Item duplicado encontrado: {url}")
        else:
            # Si es nuevo, lo añadimos al conjunto y lo pasamos al siguiente pipeline.
            self.urls_seen.add(url)
            return item

# ===============================================
# TU PIPELINE DE LIMPIEZA EXISTENTE
# ===============================================


class DataCleaningPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Obtenemos los códigos del spider
        country_code = adapter.get('country_code', '').upper()
        currency_code = adapter.get('currency_code')

        # --- 1. Limpieza de Precio y Moneda (BASADA EN PAÍS) ---
        price_str = adapter.get('price')
        if price_str:
            cleaned_str = re.sub(r'[^\d,.]', '', price_str)
            
            # Países que usan coma como separador decimal (ej: Argentina, España, Brasil)
            countries_with_comma_decimal = ['AR', 'ES', 'BR', 'DE', 'FR', 'IT']
            
            if country_code in countries_with_comma_decimal:
                # Formato: 1.234,56 -> Quitar puntos, reemplazar coma por punto
                cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
            else:
                # Formato por defecto (US, MX, UK, etc.): 1,234.56 -> Quitar comas
                cleaned_str = cleaned_str.replace(',', '')
            
            try:
                adapter['price_numeric'] = float(cleaned_str)
                adapter['currency'] = currency_code
            except (ValueError, TypeError):
                adapter['price_numeric'] = None
                adapter['currency'] = None
        else:
             adapter['price_numeric'] = None
             adapter['currency'] = None

        # --- 2. Limpieza de Rating (no cambia) ---
        rating_str = adapter.get('rating_str')
        if rating_str:
            try:
                numeric_part = rating_str.split(' ')[0]
                adapter['rating'] = float(numeric_part.replace(',', '.'))
            except (ValueError, TypeError):
                adapter['rating'] = 0.0
        else:
            adapter['rating'] = 0.0

        # --- 3. Limpieza de Cantidad de Reseñas (no cambia) ---
        reviews_str = adapter.get('reviews_count_str')
        if reviews_str:
            cleaned_reviews = reviews_str.replace('(', '').replace(')', '').replace(',', '')
            num_part = re.findall(r'[\d.]+', cleaned_reviews)
            if num_part:
                num_str = num_part[0]
                multiplier = 1
                if 'K' in cleaned_reviews.upper(): multiplier = 1000
                elif 'M' in cleaned_reviews.upper(): multiplier = 1000000
                try:
                    adapter['reviews_count'] = int(float(num_str) * multiplier)
                except (ValueError, TypeError): adapter['reviews_count'] = 0
            else:
                adapter['reviews_count'] = 0
        else:
            adapter['reviews_count'] = 0
        
        # Eliminar campos crudos
        adapter.pop('price', None)
        adapter.pop('rating_str', None)
        adapter.pop('reviews_count_str', None)
        adapter.pop('currency_code', None)
        adapter.pop('country_code', None) # <-- Limpiamos el nuevo campo también
        
        return item