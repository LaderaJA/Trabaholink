#!/bin/bash
# Docker Compose wrapper for production
# Usage: ./dc.sh [docker-compose commands]
# Example: ./dc.sh up -d
#          ./dc.sh ps
#          ./dc.sh logs -f

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production "$@"
