#Cheapy
Cheapy es un proyecto de web scraping que integra una extensión de navegador y un servidor backend para recolectar, organizar y mostrar información sobre productos buscados en tiendas online.

Actualmente permite obtener resultados de Mercado Libre, mostrando precios y reseñas de forma ordenada.

🚧 Arquitectura cliente-servidor:

Extensión (cliente): interfaz ligera en el navegador.

Servidor (backend): maneja scraping, consultas y procesamiento de datos.

🛠️ Tecnologías utilizadas
Frontend / Extensión:

HTML

CSS

JavaScript

Backend / Scraping:

FastAPI

Uvicorn

Scrapy

BeautifulSoup4

httpx

Crochet

🚀 Instalación y uso
1. Clonar el repositorio
git clone *****Completar****
cd cheapy
2. Configurar el servidor
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar el servidor
uvicorn main:app --reload
3. Instalar la extensión en Chrome/Chromium
Abrí chrome://extensions/.

Activá Modo desarrollador.

Seleccioná Cargar descomprimida y elegí la carpeta /extension.

4. Buscar un producto

El servidor hará el scraping en Mercado Libre y mostrará los resultados.

📌 Estado del proyecto
Actualmente el proyecto se encuentra en fase de desarrollo funcional, con integración inicial a Mercado Libre.

🔮 Próximos pasos
Añadir más tiendas online.

Mejorar la interfaz de la extensión.

Optimizar el rendimiento del scraping.

🤝 Contribuciones
Este es un proyecto personal para fines académicos, pero cualquier sugerencia o mejora es bienvenida.
