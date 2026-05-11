FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium --with-deps

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
pkill -9 -f chrome 2>/dev/null || true\n\
pkill -9 -f chromedriver 2>/dev/null || true\n\
exec python -m uvicorn ical_server:app --host 0.0.0.0 --port 8085\n' > /app/start.sh && \
    chmod +x /app/start.sh

ENV HEADLESS=true
ENV AIRBNB_PROFILE_DIR=/tmp/avi_profile
ENV PYTHONUNBUFFERED=1

EXPOSE 8085

CMD ["/app/start.sh"]
