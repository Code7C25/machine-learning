import sqlite3
import os


class SQLitePipeline:
    def open_spider(self, spider):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'productos.db')
        # ensure directory
        db_path = os.path.abspath(db_path)
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consulta TEXT,
                titulo TEXT,
                precio_num REAL,
                precio_raw TEXT,
                dominio TEXT,
                link TEXT,
                clasificacion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def process_item(self, item, spider):
        self.cur.execute('''INSERT INTO resultados (consulta, titulo, precio_num, precio_raw, dominio, link)
                            VALUES (?, ?, ?, ?, ?, ?)''', (
            item.get('query'), item.get('title'), item.get('price_num'), item.get('price_raw'), item.get('domain'), item.get('link')
        ))
        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.conn.close()
