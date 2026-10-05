#!/usr/bin/env bash
# Isolated local QA instance, production-equivalent: the packaged release, real entrypoint, real cookies
# (__Host-, Secure), HTTPS via a throwaway self-signed certificate for the canonical host.
# Usage: deploy/run-qa.sh <data-dir> [port=3188]
# Clients must resolve ashfall.teknetik.co to 127.0.0.1:<port>, e.g.
#   chromium --host-resolver-rules="MAP ashfall.teknetik.co:443 127.0.0.1:3188" --ignore-certificate-errors
#   curl -k -H 'Host: ashfall.teknetik.co' https://127.0.0.1:3188/api/health
set -euo pipefail
DATA="${1:?usage: run-qa.sh <data-dir> [port]}"
PORT="${2:-3188}"
REL="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$DATA"; chmod 700 "$DATA"
if [ ! -f "$DATA/cert.pem" ]; then
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
    -keyout "$DATA/key.pem" -out "$DATA/cert.pem" -days 30 \
    -subj /CN=ashfall.teknetik.co -addext subjectAltName=DNS:ashfall.teknetik.co,IP:127.0.0.1 2>/dev/null
  chmod 600 "$DATA/key.pem"
fi
export ASHFALL_PUBLIC_ORIGIN=https://ashfall.teknetik.co
export ASHFALL_DB_PATH="$DATA/community.sqlite"
export ASHFALL_HOST=127.0.0.1
export ASHFALL_PORT="$PORT"
export ASHFALL_TLS_CERT="$DATA/cert.pem"
export ASHFALL_TLS_KEY="$DATA/key.pem"
cd "$REL"
node server/cli.mjs migrate
exec node server/index.mjs
