import scrapy
import re

class EbaySpider(scrapy.Spider):
    name = "ebay"

    def __init__(self, query="", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.start_url = f"https://www.ebay.com/sch/i.html?_nkw={self.query.replace(' ', '+')}"
    
    def start_requests(self):
        yield scrapy.Request(url=self.start_url, callback=self.parse, errback=self.handle_error)

    def parse(self, response):
        items = response.css('li.s-item')
        self.logger.info(f"EbaySpider: Encontrados {len(items)} items.")

        item_count = 0
        for item in items[1:16]:
            title = item.css('div.s-item__title span[role=heading]::text').get()
            price = item.css('span.s-item__price::text').get()
            url = item.css('a.s-item__link::attr(href)').get()
            
            # --- SELECTOR DE VENTAS CORREGIDO Y MÁS ROBUSTO ---
            # Buscamos cualquier span que contenga la palabra "sold" (vendidos)
            sold_text_element = item.xpath('.//span[contains(text(), "sold")]/text()').get()
            
            reliability_score = self.calculate_ebay_reliability_from_sales(sold_text_element)
            
            if title and price and url:
                item_count += 1
                yield {
                    "title": title.strip(),
                    "price": price.strip(),
                    "url": url,
                    "source": "eBay",
                    "reliability_score": reliability_score
                }
        self.logger.info(f"EbaySpider: Extraídos {item_count} productos.")

    def calculate_ebay_reliability_from_sales(self, sold_text: str) -> int:
        if not sold_text: return 1
        try:
            numbers = re.findall(r'(\d+\.?\d*)', sold_text)
            if not numbers: return 1
            sales = float(numbers[0])
            if 'K' in sold_text.upper(): sales *= 1000
            if sales > 1000: return 5
            if sales > 500: return 4
            if sales > 100: return 3
            if sales > 10: return 2
            return 1
        except: return 1

    def handle_error(self, failure):
        self.logger.error(f"FALLO en petición. Razón: {repr(failure)}")