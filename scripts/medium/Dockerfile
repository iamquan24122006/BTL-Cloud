FROM php:8.3-apache-bookworm@sha256:b79a53c3fb1dd4b9f350a8d99d84951512b6c21044e61bbecfee8af030b3722e
ARG RELEASE_COMMIT
ARG MOODLE_COMMIT
LABEL org.opencontainers.image.revision=$RELEASE_COMMIT
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates curl libicu-dev libzip-dev libpng-dev libjpeg62-turbo-dev \
      libfreetype6-dev libpq-dev libxml2-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j2 gd intl zip soap pgsql pdo_pgsql bcmath opcache \
    && pecl install redis-6.1.0 && docker-php-ext-enable redis \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && git init /var/www/moodle && cd /var/www/moodle \
    && git remote add origin https://github.com/moodle/moodle.git \
    && git fetch --depth 1 origin tag v4.5.15 \
    && test "$(git rev-parse 'v4.5.15^{commit}')" = "$MOODLE_COMMIT" \
    && git checkout --detach "$MOODLE_COMMIT" && rm -rf .git \
    && curl -fsSL --retry 3 https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /etc/ssl/certs/rds-global.pem \
    && printf 'Listen 8080\n' >/etc/apache2/ports.conf \
    && a2dissite 000-default && a2enmod rewrite headers \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/moodle.ini /usr/local/etc/php/conf.d/99-moodle.ini
COPY scripts/medium/apache.conf /etc/apache2/sites-available/medium.conf
COPY scripts/medium/*.php /opt/moodle-medium/
RUN cp /opt/moodle-medium/config.php /var/www/moodle/config.php \
    && cp /opt/moodle-medium/ready.php /var/www/moodle/_ready.php \
    && printf 'auto_prepend_file=/opt/moodle-medium/gate.php\n' >/usr/local/etc/php/conf.d/98-gate.ini \
    && a2ensite medium && apache2ctl configtest \
    && php -r 'foreach (["curl","dom","gd","intl","mbstring","pgsql","redis","soap","sodium","xml","zip"] as $e) {if (!extension_loaded($e)) {exit(1);}}'
WORKDIR /var/www/moodle
STOPSIGNAL SIGWINCH
