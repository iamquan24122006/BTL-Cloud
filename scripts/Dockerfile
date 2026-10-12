# Official PHP image, pinned by registry digest; host OS remains Ubuntu 26.04.
FROM php:8.3-apache-bookworm@sha256:b79a53c3fb1dd4b9f350a8d99d84951512b6c21044e61bbecfee8af030b3722e

RUN apt-get update \
    && apt-get install -y --no-install-recommends libicu-dev libzip-dev libpng-dev \
       libjpeg62-turbo-dev libfreetype6-dev libpq-dev libxml2-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j2 gd intl zip soap pgsql pdo_pgsql bcmath opcache \
    && rm -rf /var/lib/apt/lists/* \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && printf 'Listen 127.0.0.1:8080\n' >/etc/apache2/ports.conf \
    && a2dissite 000-default \
    && install -d -o www-data -g www-data /var/www/moodle

COPY moodle.ini /usr/local/etc/php/conf.d/99-moodle.ini
COPY moodle-apache.conf /etc/apache2/sites-available/moodle.conf
RUN a2ensite moodle \
    && apache2ctl configtest \
    && php -r 'foreach (["curl", "dom", "gd", "intl", "mbstring", "pgsql", "pdo_pgsql", "soap", "sodium", "xml", "zip"] as $extension) { if (!extension_loaded($extension)) { fwrite(STDERR, "Missing extension: $extension\n"); exit(1); } } if (PHP_MAJOR_VERSION !== 8 || PHP_MINOR_VERSION !== 3) { exit(1); }'

WORKDIR /var/www/moodle
STOPSIGNAL SIGWINCH
