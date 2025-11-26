import re
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class ValidationPipeline:
    """
    Pipeline de validación para asegurar la integridad básica de los items extraídos.

    Implementa reglas mínimas de calidad para descartar items incompletos
    de manera consistente across todos los spiders. Verifica la presencia
    de campos críticos como URL e imagen para evitar contenido no válido
    como anuncios o elementos promocionales.
    """

    def process_item(self, item, spider):
        """
        Valida la presencia de campos obligatorios en el item.

        Args:
            item: Item extraído por el spider.
            spider: Instancia del spider (utilizado para contexto de logging).

        Returns:
            Item: El item si pasa validación.

        Raises:
            DropItem: Si faltan campos críticos como URL o imagen.
        """
        adapter = ItemAdapter(item)

        # Validación defensiva de campos obligatorios
        if not adapter.get('url'):
            raise DropItem("Item sin URL: descartado por ValidationPipeline")

        if not adapter.get('image_url'):
            raise DropItem("Item sin image_url: descartado por ValidationPipeline")

        return item


class DuplicatesPipeline:
    """
    Pipeline de deduplicación basado en URLs normalizadas.

    Utiliza un conjunto en memoria para rastrear URLs procesadas durante
    la ejecución del spider, previniendo duplicados y optimizando el
    rendimiento al evitar re-procesamiento de items idénticos.
    """

    def __init__(self):
        """
        Inicializa el conjunto para rastreo de URLs vistas.
        """
        self.urls_seen = set()

    def process_item(self, item, spider):
        """
        Verifica y registra URLs para prevenir duplicados.

        Args:
            item: Item candidato a procesamiento.
            spider: Instancia del spider para logging contextual.

        Returns:
            Item: El item si no es duplicado.

        Raises:
            DropItem: Si la URL ya fue procesada anteriormente.
        """
        adapter = ItemAdapter(item)
        url = adapter.get('url')

        # Validación crítica: items sin URL no pueden ser deduplicados
        if not url:
            raise DropItem("Item sin URL detectado, descartando.")

        if url in self.urls_seen:
            # Logging de debug para monitoreo de duplicados
            spider.logger.debug(f"Descartando ítem duplicado: {adapter.get('title', 'N/A')} - {url}")
            raise DropItem(f"Item duplicado encontrado: {url}")
        else:
            # Registrar URL nueva y continuar procesamiento
            self.urls_seen.add(url)
            return item


class DataCleaningPipeline:
    """
    Pipeline de limpieza y normalización de datos extraídos.

    Realiza transformaciones críticas en campos numéricos y textuales,
    adaptándose a diferentes formatos regionales (separadores decimales,
    monedas, sufijos numéricos). Centraliza la lógica de normalización
    para asegurar consistencia y calidad en los datos finales.
    """

    def process_item(self, item, spider):
        """
        Aplica limpieza y normalización completa al item.

        Args:
            item: Item con datos crudos del spider.
            spider: Instancia del spider para logging y contexto regional.

        Returns:
            Item: Item con datos limpios y normalizados.
        """
        adapter = ItemAdapter(item)

        # Extraer metadatos de localización para lógica de formateo
        country_code = adapter.get('country_code', '').upper()
        currency_code = adapter.get('currency_code')

        # Normalización de precios considerando formatos regionales
        existing_price_numeric = adapter.get('price_numeric')
        price_str = adapter.get('price')

        if price_str:
            # Remover caracteres no numéricos preservando separadores
            cleaned_str = re.sub(r'[^\d,.]', '', price_str)

            # Países que utilizan coma como separador decimal
            countries_with_comma_decimal = ['AR', 'ES', 'BR', 'DE', 'FR', 'IT']

            if country_code in countries_with_comma_decimal:
                # Convertir formato europeo: "1.234,56" -> "1234.56"
                cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
            else:
                # Convertir formato americano: "1,234.56" -> "1234.56"
                cleaned_str = cleaned_str.replace(',', '')

            try:
                adapter['price_numeric'] = float(cleaned_str)
                adapter['currency'] = currency_code
            except (ValueError, TypeError):
                adapter['price_numeric'] = None
                adapter['currency'] = None
        elif existing_price_numeric is not None:
            # Preservar precio numérico si ya fue establecido por el spider
            adapter['currency'] = currency_code
        else:
            adapter['price_numeric'] = None
            adapter['currency'] = None

        # Procesamiento del precio anterior para cálculo de descuentos
        price_before_str = adapter.get('price_before')
        if price_before_str:
            cleaned_before = re.sub(r'[^\d,.]', '', price_before_str)
            if country_code in ['AR', 'ES', 'BR', 'DE', 'FR', 'IT']:
                cleaned_before = cleaned_before.replace('.', '').replace(',', '.')
            else:
                cleaned_before = cleaned_before.replace(',', '')
            try:
                adapter['price_before_numeric'] = float(cleaned_before)
            except (ValueError, TypeError):
                adapter['price_before_numeric'] = None
        else:
            adapter['price_before_numeric'] = None

        # Normalización de ratings con manejo de formatos mixtos
        rating_str = adapter.get('rating_str')
        if rating_str:
            try:
                # Extraer componente numérica principal
                numeric_part = rating_str.split(' ')[0]
                adapter['rating'] = float(numeric_part.replace(',', '.'))
            except (ValueError, TypeError):
                adapter['rating'] = 0.0
        else:
            adapter['rating'] = 0.0

        # Normalización avanzada de conteos de reseñas con sufijos
        reviews_str = adapter.get('reviews_count_str')
        adapter['reviews_count_raw'] = reviews_str  # Preservar original para debugging

        if reviews_str:
            # Priorizar números explícitos entre paréntesis
            paren_match = re.search(r'\(([\d\.,]+)\)', reviews_str)
            if paren_match:
                par_num = paren_match.group(1)
                norm = par_num
                # Normalizar separadores en números parentéticos
                if '.' in norm and ',' in norm:
                    norm = norm.replace('.', '').replace(',', '.')
                elif '.' in norm and ',' not in norm:
                    parts = norm.split('.')
                    if len(parts[-1]) == 3:
                        norm = ''.join(parts)
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
                # Procesamiento de strings complejos sin paréntesis
                orig = reviews_str

                # Separar rating y ventas si están delimitados por '|'
                if '|' in orig:
                    orig = orig.split('|')[-1]

                # Limpiar y normalizar string
                s = orig.replace('(', '').replace(')', '').replace('+', '').lower()
                s = s.replace('vendidos', '').replace('vendido', '').strip()

                # Detectar patrón numérico con sufijo multiplicador
                m = re.search(r'([\d\.,]+)\s*(millones|millon|mil|k|m)?', s, re.IGNORECASE)
                if m:
                    num_str = m.group(1)
                    suffix_raw = (m.group(2) or '').lower()

                    # Calcular multiplicador basado en sufijo
                    multiplier = 1
                    if suffix_raw in ('k', 'mil'):
                        multiplier = 1000
                    elif suffix_raw in ('m', 'millon', 'millones'):
                        multiplier = 1000000

                    # Normalizar separadores considerando presencia de sufijo
                    norm = num_str
                    if suffix_raw in ('k', 'mil', 'm', 'millon', 'millones'):
                        norm = norm.replace(',', '.')
                    else:
                        # Heurística para números sin sufijo explícito
                        if '.' in norm and ',' in norm:
                            norm = norm.replace('.', '').replace(',', '.')
                        elif '.' in norm and ',' not in norm:
                            parts = norm.split('.')
                            if len(parts[-1]) == 3:
                                norm = ''.join(parts)
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

                    # Monitoreo de valores extremos para calidad de datos
                    try:
                        if adapter.get('reviews_count', 0) > 1000000:
                            msg = (
                                f"[DataCleaningPipeline] Conteo de reseñas alto detectado: "
                                f"raw={reviews_str!r} -> parsed={adapter['reviews_count']} "
                                f"title={adapter.get('title', 'N/A')!r}"
                            )
                            if spider and hasattr(spider, 'logger'):
                                spider.logger.warning(msg)
                            else:
                                print(msg)
                    except Exception:
                        pass  # No interrumpir pipeline por fallos de logging
                else:
                    adapter['reviews_count'] = 0
        else:
            adapter['reviews_count'] = 0

        # Preservar versión display del precio antes de limpieza final
        adapter['price_display'] = adapter.get('price')

        # Eliminar campos crudos innecesarios para output final
        fields_to_remove = ['price', 'rating_str', 'reviews_count_str', 'currency_code', 'country_code']
        for field in fields_to_remove:
            adapter.pop(field, None)

        return item