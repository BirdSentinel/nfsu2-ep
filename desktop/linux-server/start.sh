#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ "$(id -u)" != 0 ]; then
  echo 'Run: sudo bash start.sh' >&2; exit 1
fi
case "$(uname -m)" in x86_64|amd64) ;; *) echo 'This package requires an x86-64 VPS.' >&2; exit 1 ;; esac
docker info >/dev/null
docker compose version >/dev/null
sha256sum -c SHA256SUMS
mkdir -p data
if [ ! -f data/server.json ]; then cp server.example.json data/server.json; fi
# Only the data directory needs ownership; never replace existing server settings.
chown 10001:10001 data
docker build --network=none --pull=false -t egyuttparkolas-server:local .
docker compose up -d --wait --wait-timeout 60
echo
echo 'Server is running. Launcher address: http://YOUR-VPS-IP:8080'
echo 'Allow inbound TCP 8080 in your hosting firewall.'
echo 'Logs: sudo docker compose logs -f --tail=100'
