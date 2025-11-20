# 🐳 Trabaholink Docker Setup

This guide will help you run Trabaholink using Docker containers.

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB of free disk space
- 4GB RAM minimum (8GB recommended)

## 🚀 Quick Start

### 1. Setup Environment Variables

```bash
# Copy the example environment file
cp .env.docker.example .env.docker

# Edit the file and update the values
nano .env.docker
```

**Important:** Change at least these values:
- `SECRET_KEY` - Generate a new one: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DB_PASSWORD` - Use a strong password
- `DJANGO_SUPERUSER_*` - Uncomment and set your admin credentials

### 2. Build and Start Services

```bash
# Build the Docker images (first time only, or after Dockerfile changes)
docker-compose build

# Start all services
docker-compose --env-file .env.docker up -d

# View logs
docker-compose logs -f
```

### 3. Access the Application

- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 4. Create a Superuser (if not auto-created)

```bash
docker-compose exec web python manage.py createsuperuser
```

## 🛠️ Common Commands

### Managing Services

```bash
# Start services
docker-compose --env-file .env.docker up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart web

# View logs
docker-compose logs -f web
docker-compose logs -f celery_worker

# View all running containers
docker-compose ps
```

### Database Operations

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create database backup
docker-compose exec db pg_dump -U postgres trabaholink > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres trabaholink < backup.sql

# Access PostgreSQL shell
docker-compose exec db psql -U postgres -d trabaholink
```

### Django Management Commands

```bash
# Run any Django management command
docker-compose exec web python manage.py <command>

# Examples:
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic
docker-compose exec web python manage.py shell
```

### Celery Operations

```bash
# Monitor Celery tasks
docker-compose exec celery_worker celery -A Trabaholink inspect active

# Purge all Celery tasks
docker-compose exec celery_worker celery -A Trabaholink purge

# Check Celery worker status
docker-compose exec celery_worker celery -A Trabaholink status
```

## 🔧 Development vs Production

### Development Mode

```bash
# Use development settings
DEBUG=True docker-compose --env-file .env.docker up
```

### Production Mode

For production, create a `docker-compose.prod.yml` (coming in Phase 3) with:
- Nginx reverse proxy
- SSL/TLS certificates
- Optimized settings
- Volume backups

## 📦 Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Network                      │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   Web    │  │  Celery  │  │  Celery  │            │
│  │ (Daphne) │  │  Worker  │  │   Beat   │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │              │                   │
│       └─────────────┴──────────────┘                   │
│                     │                                   │
│       ┌─────────────┴──────────────┐                   │
│       │                            │                   │
│  ┌────▼─────┐              ┌───────▼────┐             │
│  │PostgreSQL│              │   Redis    │             │
│  │ (PostGIS)│              │            │             │
│  └──────────┘              └────────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Change ports in .env.docker
WEB_PORT=8001
DB_PORT=5433
REDIS_PORT=6380
```

### Permission Errors

```bash
# Fix volume permissions
docker-compose exec web chown -R appuser:appuser /app/mediafiles
```

### Database Connection Issues

```bash
# Check if PostgreSQL is ready
docker-compose exec db pg_isready -U postgres

# View database logs
docker-compose logs db
```

### Rebuild from Scratch

```bash
# Stop and remove everything
docker-compose down -v

# Remove old images
docker-compose rm -f
docker rmi trabaholink_web trabaholink_celery_worker

# Rebuild
docker-compose build --no-cache
docker-compose --env-file .env.docker up -d
```

## 📊 Monitoring

### Check Service Health

```bash
# Check all services
docker-compose ps

# Check specific service health
docker inspect trabaholink_web --format='{{.State.Health.Status}}'
```

### Resource Usage

```bash
# View resource usage
docker stats

# View disk usage
docker system df
```

## 🔐 Security Notes

1. **Never commit** `.env.docker` with real credentials
2. **Change default passwords** in production
3. **Use secrets management** for sensitive data
4. **Keep images updated** regularly
5. **Limit exposed ports** in production

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Verify environment variables: `docker-compose config`
3. Check service health: `docker-compose ps`
4. Restart services: `docker-compose restart`

## 🔄 Updating

```bash
# Pull latest code
git pull

# Rebuild images
docker-compose build

# Restart services
docker-compose --env-file .env.docker up -d

# Run new migrations
docker-compose exec web python manage.py migrate
```

## 🧹 Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes (WARNING: deletes data!)
docker-compose down -v

# Clean up unused Docker resources
docker system prune -a
```

---

## ✅ What's Working

- ✅ Django application with Daphne ASGI server
- ✅ PostgreSQL with PostGIS support
- ✅ Redis for caching and message broker
- ✅ Celery worker for background tasks
- ✅ Celery Beat for scheduled tasks
- ✅ WebSocket support via Channels
- ✅ OCR and face recognition dependencies
- ✅ Automatic migrations on startup

## 🚧 Coming Soon (Phase 2 & 3)

- Nginx reverse proxy
- SSL/TLS support
- Production optimizations
- Vue.js frontend container
- Backup automation
- Monitoring dashboards
