# 🏭 Trabaholink Production Deployment Guide

This guide covers deploying Trabaholink to production with Docker, Nginx, and SSL/TLS.

## 📋 Prerequisites

- **Server**: Ubuntu 20.04+ or similar Linux server
- **Domain**: A registered domain pointing to your server
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Ports**: 80 (HTTP) and 443 (HTTPS) open in firewall
- **Resources**: Minimum 4GB RAM, 2 CPU cores, 20GB disk space

---

## 🚀 Quick Production Setup

### Step 1: Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Clone and Configure

```bash
# Clone repository
git clone <your-repo-url> trabaholink
cd trabaholink/Trabaholink

# Create production environment file
cp .env.production.example .env.production

# Edit with your production values
nano .env.production
```

**Important variables to update:**
- `SECRET_KEY` - Generate a new one
- `DOMAIN_NAME` - Your domain (e.g., trabaholink.com)
- `DB_PASSWORD` - Strong database password
- `REDIS_PASSWORD` - Strong Redis password
- `EMAIL_*` - Your email SMTP settings
- `DJANGO_SUPERUSER_*` - Admin credentials

### Step 3: SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended for Production)

```bash
# Make sure your domain DNS is pointing to this server
# Then run the Let's Encrypt setup script
sudo ./scripts/setup-letsencrypt.sh
```

#### Option B: Self-Signed Certificate (Testing Only)

```bash
./scripts/generate-ssl-cert.sh
```

### Step 4: Deploy

```bash
# Build and start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 5: Verify Deployment

```bash
# Check health
curl https://yourdomain.com/health/

# Access admin panel
https://yourdomain.com/admin
```

---

## 🛠️ Production Management

### Deployment Script

Use the automated deployment script for zero-downtime deployments:

```bash
./scripts/deploy.sh
```

This script:
1. ✅ Creates automatic database backup
2. ✅ Pulls latest code from Git
3. ✅ Builds new Docker images
4. ✅ Performs rolling restart
5. ✅ Runs health checks
6. ✅ Cleans up old images

### Database Backups

#### Create Backup

```bash
./scripts/backup-database.sh
```

Backups are stored in `backups/postgres/` with timestamps.

#### Restore Backup

```bash
./scripts/restore-database.sh
```

Interactively select from available backups.

#### Automated Backups

Add to crontab for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/trabaholink/Trabaholink/scripts/backup-database.sh >> /var/log/trabaholink-backup.log 2>&1
```

### Monitoring

#### Real-time Monitor

```bash
./scripts/monitor.sh
```

#### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f nginx
docker-compose logs -f celery_worker

# Last 100 lines
docker-compose logs --tail=100 web
```

#### Check Resource Usage

```bash
docker stats
```

#### Service Health

```bash
# Basic health check
curl https://yourdomain.com/health/

# Detailed health check (includes DB, Redis)
curl https://yourdomain.com/health/detailed/
```

---

## 🔧 Service Management

### Start/Stop Services

```bash
# Start all services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart web
docker-compose restart nginx
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# Run migrations
docker-compose exec web python manage.py migrate
```

### Scale Services

```bash
# Scale Celery workers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d --scale celery_worker=4
```

---

## 🔐 Security Best Practices

### 1. Environment Variables

- ✅ Never commit `.env.production` to Git
- ✅ Use strong passwords (20+ characters)
- ✅ Rotate secrets regularly
- ✅ Use different credentials for dev/prod

### 2. SSL/TLS

- ✅ Always use Let's Encrypt in production
- ✅ Enable HSTS headers (already configured)
- ✅ Use TLS 1.2+ only (already configured)
- ✅ Certificate auto-renewal is enabled

### 3. Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 4. Database

- ✅ Database is not exposed externally (production config)
- ✅ Use strong passwords
- ✅ Regular backups
- ✅ Enable PostgreSQL connection limits

### 5. Django Settings

- ✅ `DEBUG=False` in production
- ✅ `SECRET_KEY` is unique and secure
- ✅ `ALLOWED_HOSTS` is properly configured
- ✅ Security headers enabled in Nginx

---

## 📊 Architecture Overview

```
Internet
    │
    ├─── Port 80 (HTTP) ────────┐
    │                           │
    └─── Port 443 (HTTPS) ──────┤
                                │
                            ┌───▼────┐
                            │  Nginx │ (Reverse Proxy)
                            │  + SSL │
                            └───┬────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                ┌───▼────┐  ┌──▼───┐  ┌────▼─────┐
                │  Web   │  │Redis │  │PostgreSQL│
                │(Daphne)│  │      │  │ +PostGIS │
                └───┬────┘  └──┬───┘  └────┬─────┘
                    │          │           │
            ┌───────┴──────┐   │           │
            │              │   │           │
        ┌───▼────┐    ┌────▼───▼───┐      │
        │ Celery │    │   Celery   │◄─────┘
        │  Beat  │    │   Worker   │
        └────────┘    └────────────┘
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs web

# Rebuild from scratch
docker-compose down -v
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
```

### SSL Certificate Issues

```bash
# Check certificate status
docker-compose logs certbot

# Manually renew
docker-compose run --rm certbot renew

# Regenerate self-signed cert (testing only)
./scripts/generate-ssl-cert.sh
```

### Database Connection Failed

```bash
# Check if DB is running
docker-compose exec db pg_isready -U postgres

# Check DB logs
docker-compose logs db

# Restart DB
docker-compose restart db
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a
docker volume prune

# Check volumes
docker volume ls
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Restart memory-heavy services
docker-compose restart celery_worker

# Adjust resource limits in docker-compose.prod.yml
```

---

## 📈 Performance Optimization

### 1. Enable Caching

Django caching is already configured with Redis. Optimize further:

```python
# In settings.py, add page caching for static content
CACHE_MIDDLEWARE_SECONDS = 600
```

### 2. Database Optimization

```bash
# Analyze and vacuum database
docker-compose exec db psql -U postgres -d trabaholink -c "VACUUM ANALYZE;"

# Check slow queries
docker-compose exec db psql -U postgres -d trabaholink -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### 3. Static File CDN

Consider using AWS CloudFront or similar CDN for static files.

### 4. Application Performance

```bash
# Monitor Celery tasks
docker-compose exec celery_worker celery -A Trabaholink inspect active

# Check queue length
docker-compose exec redis redis-cli LLEN celery
```

---

## 🔄 Update Checklist

Before each deployment:

- [ ] Test changes locally
- [ ] Update dependencies in requirements.txt
- [ ] Create database backup
- [ ] Review environment variables
- [ ] Check disk space
- [ ] Notify users of maintenance (if needed)
- [ ] Run migrations in a transaction
- [ ] Monitor logs after deployment
- [ ] Verify health endpoints
- [ ] Check SSL certificate expiry

---

## 📞 Support & Maintenance

### Log Locations

- Application: `docker-compose logs web`
- Nginx: `docker-compose logs nginx`
- Database: `docker-compose logs db`
- Celery: `docker-compose logs celery_worker`

### Health Endpoints

- Basic: `https://yourdomain.com/health/`
- Detailed: `https://yourdomain.com/health/detailed/`

### Backup Locations

- Database: `./backups/postgres/`
- Logs: `/var/log/nginx/` (inside Nginx container)

---

## 🎓 Additional Resources

- [Docker Documentation](https://docs.docker.com)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [PostgreSQL Best Practices](https://www.postgresql.org/docs/current/performance-tips.html)

---

**Need help?** Check the troubleshooting section or review the logs with `docker-compose logs -f`
