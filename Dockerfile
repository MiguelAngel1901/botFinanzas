# Imagen base de Python 3.11 ligera
FROM python:3.11-slim

# Instalar dependencias del sistema (Tesseract OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear carpeta de trabajo
WORKDIR /app

# Copiar dependencias de Python
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Exponer puerto (Render lo usa)
EXPOSE 10000

# Comando por defecto
CMD ["python", "bot.py"]
