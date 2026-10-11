ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20

# Build UI inside the image so the add-on context is self-contained
FROM node:22-alpine AS frontend-build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ${BUILD_FROM}
WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=frontend-build /src/dist /app/frontend/dist
COPY run.sh /run.sh
RUN chmod a+x /run.sh

ENV PYTHONPATH=/app
ENV DATA_DIR=/data
ENV STATIC_DIR=/app/frontend/dist
ENV ALLOW_ALL_HOSTS=false

CMD ["/run.sh"]
