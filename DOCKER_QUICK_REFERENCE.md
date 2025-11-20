# 🐳 Docker Quick Reference - Trabaholink

## 🚀 Getting Started (30 seconds)

```bash
cd Trabaholink
./docker-start.sh
```

That's it! Your app will be running at http://localhost:8000

---

## 📋 Essential Commands

### Start & Stop
```bash
# Start everything
docker-compose --env-file .env.docker up -d

# Stop everything
docker-compose down

# Restart a service
docker-compose restart web
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
```

### Django Management
```bash
# Any Django command
docker-compose exec web python manage.py <command>

# Common examples:
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py collectstatic
```

### Database Operations
```bash
# Access PostgreSQL
docker-compose exec db psql -U postgres -d trabaholink

# Backup database
docker-compose exec db pg_dump -U postgres trabaholink > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres trabaholink < backup.sql
```

### Check Status
```bash
# Service status
docker-compose ps

# Resource usage
docker stats

# Health check
curl http://localhost:8000/health/
```

---

## 🔧 Configuration

### Environment File
Edit `.env.docker` to configure:
- Database credentials
- Secret keys
- Admin user
- Email settings
- Ports

### Change Ports
In `.env.docker`:
```bash
WEB_PORT=8001      # Default: 8000
DB_PORT=5433       # Default: 5432
REDIS_PORT=6380    # Default: 6379
```

---

## 🐛 Troubleshooting

### Rebuild Everything
```bash
docker-compose down
docker-compose build --no-cache
docker-compose --env-file .env.docker up -d
```

### Clean Start (removes data!)
```bash
docker-compose down -v
docker-compose --env-file .env.docker up -d
```

### View Specific Service
```bash
docker-compose logs -f web        # Django app
docker-compose logs -f db         # PostgreSQL
docker-compose logs -f redis      # Redis
docker-compose logs -f celery_worker  # Celery
```

---

## 📊 Services

| Service | Port | Purpose |
|---------|------|---------|
| web | 8000 | Django app (Daphne) |
| db | 5432 | PostgreSQL + PostGIS |
| redis | 6379 | Cache & message broker |
| celery_worker | - | Background tasks |
| celery_beat | - | Scheduled tasks |

---

## ✅ Health Checks

```bash
# Basic check
curl http://localhost:8000/health/

# Detailed check (includes DB and Redis)
curl http://localhost:8000/health/detailed/
```

---

## 🔄 Updates

```bash
# After pulling new code
docker-compose build
docker-compose --env-file .env.docker up -d
docker-compose exec web python manage.py migrate
```

---

## 🆘 Need More Help?

- 📖 Full documentation: `README_DOCKER.md`
- 📝 Setup summary: `DOCKER_SETUP_COMPLETE.md`
- 🌐 Django logs: `docker-compose logs -f web`

---

**Remember**: Your old setup (`startup.sh`) still works! Docker is optional. 🎉
