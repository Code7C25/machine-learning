import re
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem # ¡Necesitas importar esto!

# ===============================================
# VALIDACIÓN BÁSICA GLOBAL
# ===============================================

class ValidationPipeline:
    """
    Reglas mínimas para descartar ítems incompletos de forma consistente en todas las tiendas.
    - image_url obligatorio (evita tarjetas especiales/ads)
    - url obligatoria (duplicado con DuplicatesPipeline, pero defensivo)
    """
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if not adapter.get('url'):
            raise DropItem("Item sin URL: descartado por ValidationPipeline")
        if not adapter.get('image_url'):
            raise DropItem("Item sin image_url: descartado por ValidationPipeline")
        return item

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
        # Si price_numeric ya está definido (del spider), NO lo sobrescribimos
        existing_price_numeric = adapter.get('price_numeric')
        
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
        elif existing_price_numeric is not None:
            # Si no hay 'price' pero price_numeric ya existe, lo conservamos
            adapter['currency'] = currency_code
        else:
            adapter['price_numeric'] = None
            adapter['currency'] = None

        # --- 1.b Procesar precio anterior (si existe) para detectar descuentos ---
        price_before_str = adapter.get('price_before')
        if price_before_str:
            cleaned_before = re.sub(r'[^\d,.]', '', price_before_str)
            countries_with_comma_decimal = ['AR', 'ES', 'BR', 'DE', 'FR', 'IT']
            if country_code in countries_with_comma_decimal:
                cleaned_before = cleaned_before.replace('.', '').replace(',', '.')
            else:
                cleaned_before = cleaned_before.replace(',', '')
            try:
                adapter['price_before_numeric'] = float(cleaned_before)
            except (ValueError, TypeError):
                adapter['price_before_numeric'] = None
        else:
            adapter['price_before_numeric'] = None

        # --- 1.c Determinar on_sale/discount_percent será responsabilidad de api/app.py ---
        # Los spiders marcarán 'is_discounted' (bool). Aquí sólo preservamos
        # price_numeric y price_before_numeric; app.py centralizará el cálculo
        # final de 'on_sale' y 'discount_percent' para mantener consistencia.

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
        # Conservar el valor crudo para depuración/traslado a la API
        adapter['reviews_count_raw'] = reviews_str
        if reviews_str:
            # Normalizar y detectar número + sufijo (K/M)
            orig = reviews_str
            # Si hay un número explícito entre paréntesis (ej: "(1178)" o "(10000000)"), lo preferimos
            paren_match = re.search(r'\(([\d\.,]+)\)', orig)
            if paren_match:
                par_num = paren_match.group(1)
                # Normalizar separadores y devolver directamente
                norm = par_num
                if '.' in norm and ',' in norm:
                    norm = norm.replace('.', '').replace(',', '.')
                elif '.' in norm and ',' not in norm:
                    parts = norm.split('.')
                    if len(parts[-1]) == 3:
                        norm = ''.join(parts)
                    else:
                        # No comma present; keep as-is (decimal)
                        norm = norm
                elif ',' in norm and '.' not in norm:
                    parts = norm.split(',')
                    if len(parts[-1]) == 3:
                        norm = ''.join(parts)
                    else:
                        norm = norm.replace(',', '.')
                try:
                    adapter['reviews_count'] = int(float(norm))
                except Exception:
                    adapter['reviews_count'] = 0
            else:
                # Si la cadena contiene '|' (rating | ventas), preferimos la parte derecha
                if '|' in orig:
                    orig = orig.split('|')[-1]

                s = orig.replace('(', '').replace(')', '').replace('+', '').lower()
                # Eliminar etiquetas frecuentes
                s = s.replace('vendidos', '').replace('vendido', '').strip()

                # Capturamos sufijos comunes: k, m, mil, millon(es)
                # Orden importante: buscar primero tokens más largos (millones|millon|mil)
                m = re.search(r'([\d\.,]+)\s*(millones|millon|mil|k|m)?', s, re.IGNORECASE)
                if m:
                    num_str = m.group(1)
                    suffix_raw = (m.group(2) or '').lower()

                    # Detectar multiplicador por sufijo textual
                    multiplier = 1
                    if suffix_raw in ('k', 'mil'):
                        multiplier = 1000
                    elif suffix_raw in ('m', 'millon', 'millones'):
                        multiplier = 1000000

                    # Normalizar separadores:
                    # - Si hay sufijo (k/mil/million) tratamos '.' o ',' como decimal
                    #   para que '1.012K' -> 1.012 * 1000 = 1012
                    norm = num_str
                    if suffix_raw in ('k', 'mil', 'm', 'millon', 'millones'):
                        norm = norm.replace(',', '.')
                    else:
                        # Heurística para formatos sin sufijo: detectar separador de miles
                        if '.' in norm and ',' in norm:
                            norm = norm.replace('.', '').replace(',', '.')
                        elif '.' in norm and ',' not in norm:
                            parts = norm.split('.')
                            if len(parts[-1]) == 3:
                                norm = ''.join(parts)
                            else:
                                norm = norm.replace(',', '.')
                        elif ',' in norm and '.' not in norm:
                            parts = norm.split(',')
                            if len(parts[-1]) == 3:
                                norm = ''.join(parts)
                            else:
                                norm = norm.replace(',', '.')

                    try:
                        val = float(norm)
                        adapter['reviews_count'] = int(round(val * multiplier))
                    except (ValueError, TypeError):
                        adapter['reviews_count'] = 0
                    # Loguear casos sospechosos para facilitar depuración (por ejemplo 10_000_000)
                    try:
                        if adapter.get('reviews_count', 0) > 1000000:
                            msg = f"[DataCleaningPipeline] reviews_count grande detectado: raw={reviews_str!r} -> parsed={adapter['reviews_count']} title={adapter.get('title')!r}"
                            if spider and hasattr(spider, 'logger'):
                                spider.logger.warning(msg)
                            else:
                                # En entornos de test sin spider, imprimimos por consola
                                print(msg)
                    except Exception:
                        # No romper el pipeline por un fallo en logging
                        pass
                else:
                    adapter['reviews_count'] = 0
        else:
            adapter['reviews_count'] = 0

        # Antes de eliminar el campo crudo 'price', guardamos una versión para mostrar tal cual
        adapter['price_display'] = adapter.get('price')

        # Eliminar campos crudos que no queremos en el resultado final
        adapter.pop('price', None)
        adapter.pop('rating_str', None)
        adapter.pop('reviews_count_str', None)
        adapter.pop('currency_code', None)
        adapter.pop('country_code', None)
        # NOTA: conservamos price_before_numeric, price_before, on_sale y discount_percent

        return item