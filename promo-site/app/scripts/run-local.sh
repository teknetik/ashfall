#!/usr/bin/env bash
# Local QA/dev runner: production entrypoint, isolated data dir, self-signed TLS for the canonical host.
# Usage: scripts/run-local.sh <data-dir> <port>
# The browser must resolve ashfall.teknetik.co to 127.0.0.1:<port> (see README "Local QA instance").
set -euo pipefail
DATA="${1:?data dir}"
PORT="${2:?port}"
APP="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$DATA"
chmod 700 "$DATA"
if [ ! -f "$DATA/cert.pem" ]; then
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
    -keyout "$DATA/key.pem" -out "$DATA/cert.pem" -days 30 \
    -subj /CN=ashfall.teknetik.co -addext subjectAltName=DNS:ashfall.teknetik.co,IP:127.0.0.1 2>/dev/null
  chmod 600 "$DATA/key.pem"
fi
cd "$APP"
export ASHFALL_PUBLIC_ORIGIN=https://ashfall.teknetik.co
export ASHFALL_DB_PATH="$DATA/community.sqlite"
export ASHFALL_HOST=127.0.0.1
export ASHFALL_PORT="$PORT"
export ASHFALL_TLS_CERT="$DATA/cert.pem"
export ASHFALL_TLS_KEY="$DATA/key.pem"
exec node server/index.mjs
