#!/usr/bin/env bash
# Bring up a local OpenMage LTS install for the integration tests.
#
#   ./bootstrap.sh          start (and on first run download, install, seed)
#   ./bootstrap.sh --reset  wipe the containers AND volumes, then start fresh
#
# Every step checks what is already there, so re-running on an existing install
# only starts the containers and re-applies the seed data; it never reinstalls.
# Stop with "docker compose stop" (keeps the install), not "down -v".
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

OPENMAGE_VERSION=${OPENMAGE_VERSION:-20.18.0}
OPENMAGE_PORT=${OPENMAGE_PORT:-18080}
BASE_URL="http://localhost:${OPENMAGE_PORT}/"

if [[ "${1:-}" == "--reset" ]]; then
    echo "Removing containers and volumes..."
    docker compose down --volumes --remove-orphans
fi

echo "Starting containers..."
docker compose up -d --build --wait

# Run a command in the web container as the Apache user.
web() { docker compose exec -T -u www-data -w /var/www/html web "$@"; }

if ! web test -f app/Mage.php || ! web test -f vendor/autoload.php; then
    echo "Fetching OpenMage ${OPENMAGE_VERSION}..."
    web bash /opt/harness/fetch-source.sh "${OPENMAGE_VERSION}"
else
    echo "OpenMage source already present: $(web php -r 'require "app/Mage.php"; echo Mage::getOpenMageVersion();')"
fi

if ! web test -f app/etc/local.xml; then
    echo "Installing OpenMage..."
    web php install.php \
        --license_agreement_accepted yes \
        --locale en_US \
        --timezone UTC \
        --default_currency USD \
        --db_host db \
        --db_name "${DB_NAME}" \
        --db_user "${DB_USER}" \
        --db_pass "${DB_PASSWORD}" \
        --url "${BASE_URL}" \
        --secure_base_url "${BASE_URL}" \
        --use_rewrites yes \
        --use_secure no \
        --use_secure_admin no \
        --skip_url_validation yes \
        --admin_firstname Test \
        --admin_lastname Admin \
        --admin_email admin@example.com \
        --admin_username "${OPENMAGE_ADMIN_USER}" \
        --admin_password "${OPENMAGE_ADMIN_PASSWORD}"
else
    echo "OpenMage already installed (app/etc/local.xml exists)."
fi

echo "Seeding API user, catalogue, customer and checkout config..."
docker compose exec -T -u www-data -w /var/www/html \
    -e OPENMAGE_API_USER="${OPENMAGE_API_USER}" \
    -e OPENMAGE_API_KEY="${OPENMAGE_API_KEY}" \
    web php /opt/harness/seed.php

echo "Checking the XML-RPC endpoint..."
for _ in $(seq 1 20); do
    if curl -fsS -o /dev/null -H 'Content-Type: text/xml' \
        --data '<?xml version="1.0"?><methodCall><methodName>startSession</methodName></methodCall>' \
        "${BASE_URL}index.php/api/xmlrpc"; then
        break
    fi
    sleep 1
done

cat <<EOF

OpenMage is up.
  Storefront : ${BASE_URL}
  Admin      : ${BASE_URL}index.php/admin  (${OPENMAGE_ADMIN_USER} / see .env)
  API user   : ${OPENMAGE_API_USER} / see .env

Run the integration tests from the repository root:
  OPENMAGE_URL=${BASE_URL} uv run pytest -q -m openmage

Stop (keeps the install):  docker compose -f dev/openmage/docker-compose.yml stop
EOF
