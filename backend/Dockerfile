FROM python:3.12-slim

# Instalar Chrome y dependencias
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Instalar chromedriver compatible
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') \
    && wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}.0/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /tmp \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Guardar datos semilla fuera del volume para inicializar si el volume está vacío
RUN mkdir -p /app/data_seed /app/data/ics_files && \
    cp -r /app/data/. /app/data_seed/

# Script de inicio: copia datos semilla al volume si listings_data.json no existe
RUN printf '#!/bin/sh\n\
if [ ! -f /app/data/listings_data.json ]; then\n\
  echo "Initializing data from seed..."\n\
  cp -rn /app/data_seed/. /app/data/\n\
fi\n\
mkdir -p /app/data/ics_files\n\
exec python -m uvicorn ical_server:app --host 0.0.0.0 --port 8085\n' > /app/start.sh && \
    chmod +x /app/start.sh

ENV HEADLESS=true
ENV AIRBNB_PROFILE_DIR=/tmp/avi_profile
ENV PYTHONUNBUFFERED=1

EXPOSE 8085

CMD ["/app/start.sh"]
