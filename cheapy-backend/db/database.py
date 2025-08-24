import sqlite3

def init_db():
    conn = sqlite3.connect("productos.db")
    c = conn.cursor()
    c.execute("""
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
    """)
    conn.commit()
    return conn

def guardar_resultados(conn, resultados, consulta):
    c = conn.cursor()
    for r in resultados:
        c.execute("""
            INSERT INTO resultados (consulta, titulo, precio_num, precio_raw, dominio, link, clasificacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (consulta, r["titulo"], r["precio_num"], r["precio_raw"], r["dominio"], r["link"], None))
    conn.commit()
