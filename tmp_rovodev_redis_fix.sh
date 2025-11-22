'EOF'                                                                │
│  #!/bin/bash                                                                                                         │
│                                                                                                                      │
│  set -e                                                                                                              │
│                                                                                                                      │
│  echo "=========================================="                                                                   │
│  echo "Redis Connection Fix Deployment Script"                                                                       │
│  echo "=========================================="                                                                   │
│  echo ""                                                                                                             │
│                                                                                                                      │
│  REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)                                                │
│                                                                                                                      │
│  echo "Generated secure Redis password"                                                                              │
│  echo ""                                                                                                             │
│                                                                                                                      │
│  if [ ! -f .env.production ]; then                                                                                   │
│      echo "Error: .env.production file not found!"                                                                   │
│      exit 1                                                                                                          │
│  fi                                                                                                                  │
│                                                                                                                      │
│  cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)                                                    │
│  echo "Backed up .env.production"                                                                                    │
│                                                                                                                      │
│  if grep -q "^REDIS_PASSWORD=" .env.production; then                                                                 │
│      sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASSWORD}|" .env.production                                 │
│      echo "Updated existing REDIS_PASSWORD"                                                                          │
│  else                                                                                                                │
│      echo "" >> .env.production                                                                                      │
│      echo "# Redis Password (generated $(date +%Y-%m-%d))" >> .env.production                                        │
│      echo "REDIS_PASSWORD=${REDIS_PASSWORD}" >> .env.production                                                      │
│      echo "Added REDIS_PASSWORD to .env.production"                                                                  │
│  fi                                                                                                                  │
│                                                                                                                      │
│  echo ""                                                                                                             │
│  echo "=========================================="                                                                   │
│  echo "Your Redis Password (SAVE THIS!):"                                                                            │
│  echo "=========================================="                                                                   │
│  echo ""                                                                                                             │
│  echo "${REDIS_PASSWORD}"                                                                                            │
│  echo ""                                                                                                             │
│  echo "=========================================="                                                                   │
│  echo ""                                                                                                             │
│                                                                                                                      │
│  echo "${REDIS_PASSWORD}" > .redis_password.txt                                                                      │
│  chmod 600 .redis_password.txt                                                                                       │
│  echo "Password saved to: .redis_password.txt"                                                                       │
│  echo ""                                                                                                             │
│                                                                                                                      │
│  echo "Stopping services..."                                                                                         │
│  docker compose --env-file .env.production down                                                                      │
│                                                                                                                      │
│  echo ""                                                                                                             │
│  echo "Rebuilding services..."                                                                                       │
│  docker compose --env-file .env.production build                                                                     │
│                                                                                                                      │
│  echo ""                                                                                                             │
│  echo "Starting services..."                                                                                         │
│  docker compose --env-file .env.production up -d                                                                     │
│                                                                                                                      │
│  echo ""                                                                                                             │
│  echo "Waiting 10 seconds..."                                                                                        │
│  sleep 10                                                                                                            │
│                                                                                                                      │
│  echo ""                                                                                                             │
│  echo "Service status:"                                                                                              │
│  docker compose --env-file .env.production ps                                                                        │
│                                                                                                                      │
│  echo ""                                                                                                             │
│  echo "Web service logs:"                                                                                            │
│  docker compose --env-file .env.production logs --tail=30 web                                                        │
│                                                                                                                      │
│  echo ""                                                                                                             │
│  echo "=========================================="                                                                   │
│  echo "Deployment Complete!"                                                                                         │
│  echo "=========================================="                                                                   │
│  echo ""                                                                                                             │
│  echo "Your Redis password: ${REDIS_PASSWORD}"                                                                       │
│  echo "Password saved in: .redis_password.txt"                                                                       │
│  echo ""                                                                                                             │
│  EOF
