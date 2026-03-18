FROM python:3.11-slim

# Evita archivos .pyc y permite ver logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

# Dependencias para Postgres y herramientas de compilación
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Exponer el puerto de FastAPI
EXPOSE 8000

# Comando para desarrollo con recarga automática
CMD ["fastapi", "dev", "/code/app/main.py", "--host", "0.0.0.0", "--port", "8000"]
