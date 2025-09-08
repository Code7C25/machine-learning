# Cheapy

**Cheapy** es un proyecto de **web scraping** que integra una **extensión de navegador** y un **servidor backend** para recolectar, organizar y mostrar información sobre productos buscados en tiendas online.

Actualmente permite obtener resultados de **Mercado Libre**, mostrando precios y reseñas de forma ordenada.

## 🚧 Arquitectura cliente-servidor

* **Extensión (cliente):** interfaz ligera en el navegador.
* **Servidor (backend):** maneja scraping, consultas y procesamiento de datos.

## 🛠️ Tecnologías utilizadas

**Frontend / Extensión**

* HTML
* CSS
* JavaScript

**Backend / Scraping**

* FastAPI
* Uvicorn
* Scrapy
* BeautifulSoup4
* httpx
* Crochet

## 🚀 Instalación y uso

### 1. Clonar el repositorio

```bash
git clone <URL-del-repo>
cd cheapy
```

### 2. Configurar el servidor

```bash
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar el servidor
uvicorn main:app --reload
```

### 3. Instalar la extensión en Chrome/Chromium

1. Abrí `chrome://extensions/`.
2. Activá **Modo desarrollador**.
3. Seleccioná **Cargar descomprimida** y elegí la carpeta `/extension`.

### 4. Buscar un producto

* Abrí el popup de la extensión.
* Escribí el nombre de un producto.
* El servidor hará el scraping en Mercado Libre y mostrará los resultados.

## 📌 Estado del proyecto

Actualmente el proyecto se encuentra en **fase de desarrollo funcional**, con integración inicial a Mercado Libre.

## 🔮 Próximos pasos

* Añadir más tiendas online.
* Mejorar la interfaz de la extensión.
* Optimizar el rendimiento del scraping.

## 🤝 Contribuciones

Este es un proyecto personal para fines académicos, pero cualquier sugerencia o mejora es bienvenida.

---

👉 ¿Querés que también te arme una **versión con badges** (ej. Python, FastAPI, estado del proyecto, licencia) para que se vea más atractivo en GitHub?

