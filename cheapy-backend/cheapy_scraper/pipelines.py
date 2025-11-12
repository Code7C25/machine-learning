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

          # --- 2. Limpieza de Rating (ACTUALIZADO para MercadoLibre aria-label) ---
        rating_str = adapter.get('rating_str')
        if rating_str:
            # Detecta si es el formato de MercadoLibre con "Calificación X.X de 5 estrellas"
            if "Calificación" in rating_str and "estrellas" in rating_str:
                match = re.search(r'Calificación ([\d.]+)', rating_str)
                if match:
                    try:
                        adapter['rating'] = float(match.group(1))
                    except (ValueError, TypeError):
                        adapter['rating'] = 0.0
                else:
                    adapter['rating'] = 0.0
            else: # Tu lógica existente para otros formatos de rating_str
                try:
                    numeric_part = rating_str.split(' ')[0]
                    adapter['rating'] = float(numeric_part.replace(',', '.'))
                except (ValueError, TypeError):
                    adapter['rating'] = 0.0
        else:
            adapter['rating'] = 0.0

        # --- 3. Limpieza de Cantidad de Reseñas (ACTUALIZADO para MercadoLibre aria-label) ---
        reviews_str = adapter.get('reviews_count_str') # Esto recibirá el mismo aria-label
        if reviews_str:
            # Detecta si es el formato de MercadoLibre con "Más de X productos vendidos." o "Y opiniones"
            if "vendidos" in reviews_str:
                match = re.search(r'Más de ([\d.]+) productos vendidos', reviews_str)
                if match:
                    try:
                        # Asume que "Más de 1000" significa 1000, "Más de 500" significa 500
                        num_part = float(match.group(1)) 
                        adapter['reviews_count'] = int(num_part)
                    except (ValueError, TypeError):
                        adapter['reviews_count'] = 0
                else: # Si no es "Más de X vendidos", podría ser el conteo de opiniones directo.
                    # Aquí podemos intentar buscar "(X opiniones)" como un fallback.
                    opinions_match = re.search(r'\((\d+)\s*(opiniones|reseñas)\)', reviews_str)
                    if opinions_match:
                        try:
                            adapter['reviews_count'] = int(opinions_match.group(1))
                        except (ValueError, TypeError):
                            adapter['reviews_count'] = 0
                    else:
                        adapter['reviews_count'] = 0 # No se encontró un patrón claro
            else: # Tu lógica existente para otros formatos de reviews_count_str
                cleaned_reviews = reviews_str.replace('(', '').replace(')', '').replace(',', '').strip()
                num_part_match = re.search(r'([\d.]+)\s*(K|k|M|m)?', cleaned_reviews)
                if num_part_match:
                    num_str = num_part_match.group(1)
                    multiplier_char = num_part_match.group(2)
                    multiplier = 1
                    if multiplier_char and multiplier_char.upper() == 'K': multiplier = 1000
                    elif multiplier_char and multiplier_char.upper() == 'M': multiplier = 1000000
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