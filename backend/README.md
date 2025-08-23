Instalación y ejecución del backend (Python)

Requisitos:
- Python 3.8+ (preferible 3.11+)

Pasos:
1. Crear un entorno virtual (desde la raíz del proyecto):

   "C:\Users\Usuario\AppData\Local\Programs\Python\Python313\python.exe" -m venv .venv

2. Activar el entorno:

   En cmd:
   .venv\Scripts\activate

   En PowerShell:
   .\.venv\Scripts\Activate.ps1

3. Instalar dependencias:

   pip install -r backend/requirements.txt

4. Ejecutar el servidor en modo desarrollo:

   python backend/server.py

El servidor escuchará en http://localhost:3000 y expone el endpoint /buscar?q=consulta
