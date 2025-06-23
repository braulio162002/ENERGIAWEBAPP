FROM python:3.11

# Instala dependencias de sistema para WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2 \
    pango1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info

# Instala dependencias de Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia el resto de tu código
COPY . .

# Puerto por defecto para Flask/Gunicorn
ENV PORT=5000

# Comando para iniciar tu app (ajusta si tu archivo principal es main.py)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
