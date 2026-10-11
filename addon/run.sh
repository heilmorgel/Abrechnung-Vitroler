#!/usr/bin/with-contenv bashio
set -e

export DATA_DIR="/data"
export HOST="0.0.0.0"
export PORT="8099"
export STATIC_DIR="/app/frontend/dist"
export PYTHONPATH="/app"
export ALLOW_ALL_HOSTS="false"

export HA_URL="${HA_URL:-http://supervisor/core}"
export HA_TOKEN="${SUPERVISOR_TOKEN:-}"

mkdir -p "${DATA_DIR}/invoices"

if command -v bashio >/dev/null 2>&1; then
  bashio::log.info "Starting Abrechnung Vitroler on port ${PORT}"
fi

cd /app
exec python3 -m uvicorn backend.app.main:app --host "${HOST}" --port "${PORT}"
