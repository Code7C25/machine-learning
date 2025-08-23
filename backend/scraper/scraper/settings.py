BOT_NAME = 'scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

ROBOTSTXT_OBEY = False
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

ITEM_PIPELINES = {
    'scraper.pipelines.SQLitePipeline': 300,
}

LOG_LEVEL = 'INFO'
