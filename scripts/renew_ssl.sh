#!/bin/bash

# SSL Renewal Script
# This script renews certificates and reloads Nginx.
# Add this to your crontab (e.g., weekly).

set -e

PROJECT_DIR="/var/www/cnv"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$PROJECT_DIR"

echo "Starting SSL renewal..."
docker compose -f "$COMPOSE_FILE" run --rm certbot renew

echo "Reloading Nginx..."
docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload

echo "SSL renewal completed successfully."
