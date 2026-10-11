ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

WORKDIR /app

# Prepared by scripts/prepare_addon.py into addon/app/
COPY app/backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/backend/requirements.txt

COPY app/backend /app/backend
COPY app/www /app/frontend/dist
COPY run.sh /run.sh
RUN chmod a+x /run.sh

ENV PYTHONPATH=/app
ENV DATA_DIR=/data
ENV STATIC_DIR=/app/frontend/dist
ENV ALLOW_ALL_HOSTS=false

CMD ["/run.sh"]
