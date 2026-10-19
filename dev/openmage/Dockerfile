# Minimal PHP + Apache image for a throwaway OpenMage LTS test install.
#
# The OpenMage source itself is not baked in: bootstrap.sh downloads the pinned
# release into the "openmage-src" volume on first run, so the image stays small
# and the install survives image rebuilds.
FROM php:8.3-apache

# git/patch/unzip are needed by composer (cweagans/composer-patches applies
# OpenMage's vendor patches with git or patch).
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git patch unzip \
        libfreetype6-dev libjpeg62-turbo-dev libpng-dev libicu-dev libxml2-dev libzip-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" ftp gd intl mysqli pdo_mysql soap zip \
    && rm -rf /var/lib/apt/lists/* /tmp/pear

ARG COMPOSER_VERSION=2.10.3
RUN curl -fsSL "https://getcomposer.org/download/${COMPOSER_VERSION}/composer.phar" -o /usr/local/bin/composer \
    && chmod +x /usr/local/bin/composer

RUN { \
        echo 'memory_limit = 768M'; \
        echo 'max_execution_time = 300'; \
        echo 'date.timezone = UTC'; \
        echo 'display_errors = Off'; \
        echo 'log_errors = On'; \
        echo 'opcache.validate_timestamps = 1'; \
        echo 'opcache.revalidate_freq = 2'; \
    } > /usr/local/etc/php/conf.d/zz-openmage.ini

# Apache listens on the same port inside the container as on the host. The
# SOAP v1 server fetches its own WSDL from the store base URL
# (http://localhost:$OPENMAGE_PORT/...), so that URL has to resolve from inside
# the container as well as from the host.
RUN a2enmod rewrite headers \
    && sed -ri 's/^Listen 80$/Listen ${OPENMAGE_PORT}/' /etc/apache2/ports.conf \
    && sed -ri 's/<VirtualHost \*:80>/<VirtualHost *:${OPENMAGE_PORT}>/' /etc/apache2/sites-available/000-default.conf \
    && printf '<Directory /var/www/html>\n    AllowOverride All\n</Directory>\n' > /etc/apache2/conf-enabled/openmage.conf

ENV OPENMAGE_PORT=18080 \
    COMPOSER_HOME=/tmp/composer \
    COMPOSER_ALLOW_SUPERUSER=1

# Harness scripts are copied in rather than bind-mounted so the setup works
# with Docker VMs that do not share the checkout's path.
COPY scripts/ /opt/harness/
