FROM php:8.2-apache

RUN a2enmod rewrite \
    && docker-php-ext-install pdo pdo_mysql

COPY ./apache.conf /etc/apache2/sites-available/000-default.conf
WORKDIR /var/www/html
COPY ./public ./public
COPY ./src ./src

EXPOSE 80
