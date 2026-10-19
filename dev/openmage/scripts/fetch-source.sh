#!/usr/bin/env bash
# Runs inside the web container (as www-data, in /var/www/html).
# Downloads the pinned OpenMage release and installs its composer dependencies.
# Resumable: skips the download when the source is already unpacked.
set -euo pipefail
version="$1"
cd /var/www/html

if [[ ! -f app/Mage.php ]]; then
    url="https://codeload.github.com/OpenMage/magento-lts/tar.gz/refs/tags/v${version}"
    echo "Downloading ${url}"
    curl -fsSL "$url" -o /tmp/openmage.tar.gz
    tar -xzf /tmp/openmage.tar.gz --strip-components=1 -C /var/www/html
    rm -f /tmp/openmage.tar.gz
fi

if [[ ! -f vendor/autoload.php ]]; then
    composer install --no-dev --no-interaction --no-progress --prefer-dist
fi

mkdir -p var/cache var/log var/locks var/session media
