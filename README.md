# Trabaholink - Job Matching Platform

A Django-based job matching and social networking platform for connecting job seekers with employers in the Philippines.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- Ngrok account (for external access)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Trabaholink
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start development services**
   ```bash
   docker compose up -d
   ```

4. **Run migrations**
   ```bash
   docker compose exec web python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - Web: http://localhost:80
   - Admin: http://localhost:80/admin

---

## 🏭 Production Deployment

### Server Requirements
- Ubuntu 20.04+ or similar Linux distribution
- Docker & Docker Compose installed
- Domain name or Ngrok for external access
- Minimum 2GB RAM, 2 CPU cores

### Production Setup

1. **Clone on server**
   ```bash
   cd ~
   git clone <your-repo-url> Trabaholink
   cd Trabaholink
   ```

2. **Create production environment file**
   ```bash
   cp .env.production.example .env.production
   ```

3. **Configure `.env.production`**
   Edit the file with your production settings:
   ```bash
   nano .env.production
   ```

   Key variables to set:
   - `SECRET_KEY` - Django secret key (generate new one)
   - `DEBUG=False`
   - `ALLOWED_HOSTS` - Your domain/IP
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database credentials
   - `REDIS_PASSWORD` - Redis authentication
   - `EMAIL_*` - Email configuration (SendGrid recommended)
   - `DOMAIN_NAME` - Your domain name

4. **Start production services**
   ```bash
   # Use the wrapper script for convenience
   ./dc.sh up -d
   
   # Or use full command:
   # docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
   ```

5. **Run migrations**
   ```bash
   ./dc.sh exec web python manage.py migrate
   ```

6. **Collect static files**
   ```bash
   ./dc.sh exec web python manage.py collectstatic --noinput
   ```

7. **Create superuser**
   ```bash
   ./dc.sh exec web python manage.py createsuperuser
   ```

### Production Commands

The `dc.sh` wrapper script simplifies production commands:

```bash
# View all services status
./dc.sh ps

# View logs
./dc.sh logs -f                # All services
./dc.sh logs -f web            # Specific service
./dc.sh logs --tail=100 web    # Last 100 lines

# Restart services
./dc.sh restart web
./dc.sh restart nginx

# Full restart
./dc.sh down
./dc.sh up -d

# Execute commands in containers
./dc.sh exec web bash
./dc.sh exec web python manage.py shell

# Database backup
./dc.sh exec db pg_dump -U postgres trabaholink > backup_$(date +%Y%m%d).sql

# Database restore
cat backup.sql | ./dc.sh exec -T db psql -U postgres trabaholink
```

---

## 📦 Docker Services

### Core Services

- **web** - Django/Daphne application server (port 8000)
- **db** - PostgreSQL 15 with PostGIS extension (port 5433)
- **redis** - Redis for caching and Celery broker (port 6380)
- **nginx** - Reverse proxy and static file server (ports 80, 443)

### Background Services

- **celery_worker** - Processes background tasks
- **celery_beat** - Periodic task scheduler (uses django-celery-beat)
- **certbot** - SSL certificate management

### Service Health

Check service status:
```bash
./dc.sh ps
```

Expected output:
- web: healthy
- db: healthy  
- redis: healthy
- nginx: running
- celery_worker: running
- celery_beat: running

---

## 🔧 Configuration

### Environment Variables

#### Required Settings
```bash
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=trabaholink
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_PASSWORD=your-redis-password
```

#### Email Configuration (SendGrid)
```bash
EMAIL_BACKEND=sendgrid_backend.SendgridBackend
SENDGRID_API_KEY=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

#### Optional Settings
```bash
# Social Authentication
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# AWS S3 (for media storage)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=your-bucket-name
```

### SSL/HTTPS Setup

For production with domain name:

1. **Update `.env.production`**
   ```bash
   DOMAIN_NAME=yourdomain.com
   ```

2. **Generate SSL certificates**
   ```bash
   ./dc.sh run --rm certbot certonly --webroot \
     -w /var/www/certbot \
     -d yourdomain.com \
     -d www.yourdomain.com \
     --email your@email.com \
     --agree-tos \
     --no-eff-email
   ```

3. **Restart nginx**
   ```bash
   ./dc.sh restart nginx
   ```

### Ngrok Setup (Development/Testing)

If you don't have a domain:

1. **Install Ngrok**
   ```bash
   snap install ngrok
   ```

2. **Start Ngrok tunnel**
   ```bash
   ngrok http 80
   ```

3. **Update ALLOWED_HOSTS**
   Add the ngrok URL to your `.env.production`:
   ```bash
   ALLOWED_HOSTS=your-ngrok-url.ngrok-free.dev,localhost
   ```

---

## 🛠️ Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
./dc.sh build
./dc.sh up -d

# Run new migrations
./dc.sh exec web python manage.py migrate

# Collect static files
./dc.sh exec web python manage.py collectstatic --noinput
```

### Database Backups

**Automated backup script:**
```bash
#!/bin/bash
BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

cd /root/Trabaholink
./dc.sh exec -T db pg_dump -U postgres trabaholink | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

Add to crontab:
```bash
crontab -e
# Add: 0 2 * * * /root/backup_trabaholink.sh
```

### Monitoring Logs

```bash
# Watch all logs in real-time
./dc.sh logs -f

# Watch specific service
./dc.sh logs -f web
./dc.sh logs -f celery_worker

# Check for errors
./dc.sh logs web | grep -i error
./dc.sh logs nginx | grep -i error
```

### Performance Optimization

**Check container resources:**
```bash
docker stats
```

**Restart services periodically:**
```bash
# Add to crontab for weekly restart
0 3 * * 0 cd /root/Trabaholink && ./dc.sh restart celery_worker celery_beat
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
./dc.sh logs [service-name]

# Rebuild container
./dc.sh build [service-name]
./dc.sh up -d [service-name]

# Check for port conflicts
sudo netstat -tulpn | grep -E '80|443|5432|6379'
```

### Database Connection Issues

```bash
# Check database is running
./dc.sh exec db psql -U postgres -c "SELECT version();"

# Check connection from web container
./dc.sh exec web python manage.py dbshell
```

### Redis Connection Issues

```bash
# Test Redis connection
./dc.sh exec redis redis-cli -a "your-redis-password" ping

# Should return: PONG
```

### Celery Not Processing Tasks

```bash
# Check celery worker status
./dc.sh exec celery_worker celery -A Trabaholink inspect active

# Check celery beat status
./dc.sh logs celery_beat | tail -20

# Restart celery services
./dc.sh restart celery_worker celery_beat
```

### Nginx Not Serving Static Files

```bash
# Re-collect static files
./dc.sh exec web python manage.py collectstatic --noinput

# Check nginx logs
./dc.sh logs nginx

# Verify volume mounts
./dc.sh exec nginx ls -la /app/staticfiles/
```

### Out of Disk Space

```bash
# Clean up Docker
docker system prune -a --volumes

# Clean old logs
./dc.sh exec web find /app -name "*.log" -mtime +30 -delete
```

---

## 📁 Project Structure

```
Trabaholink/
├── admin_dashboard/       # Admin dashboard app
├── announcements/         # Announcements functionality
├── certbot/              # SSL certificates
├── core/                 # Core settings and utilities
├── jobs/                 # Job posting and matching
├── mediafiles/           # User uploaded files
├── messaging/            # Real-time messaging system
├── nginx/                # Nginx configuration
│   ├── Dockerfile
│   ├── nginx.conf        # Production HTTPS config
│   └── nginx-simple.conf # Development/Ngrok HTTP config
├── notifications/        # Notification system
├── posts/               # Social media posts
├── profile_pics/        # User profile pictures
├── reports/             # Reporting system
├── scripts/             # Utility scripts
├── services/            # Services marketplace
├── staticfiles/         # Collected static files
├── templates/           # Django templates
├── Trabaholink/         # Main project settings
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── asgi.py
├── users/               # User management and authentication
├── .env.example         # Example environment file
├── .env.production.example  # Production example
├── dc.sh                # Docker Compose wrapper
├── docker-compose.yml   # Base Docker Compose
├── docker-compose.prod.yml  # Production overrides
├── Dockerfile           # Application Dockerfile
├── entrypoint.sh        # Container entrypoint
├── manage.py            # Django management
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
./dc.sh exec web python manage.py test

# Run specific app tests
./dc.sh exec web python manage.py test users
./dc.sh exec web python manage.py test jobs

# Run with coverage
./dc.sh exec web coverage run --source='.' manage.py test
./dc.sh exec web coverage report
```

### Check Code Quality

```bash
# Check for issues
./dc.sh exec web python manage.py check --deploy

# Run migrations check
./dc.sh exec web python manage.py makemigrations --check --dry-run
```

---

## 📚 Key Features

- **Job Matching**: AI-powered job recommendations
- **Social Networking**: Posts, comments, likes, and sharing
- **Real-time Messaging**: WebSocket-based chat system
- **Service Marketplace**: Freelance services platform
- **Verification System**: PhilSys ID verification with OCR
- **Geolocation**: Location-based job search with PostGIS
- **Notifications**: Real-time notifications system
- **Admin Dashboard**: Comprehensive admin interface

---

## 🔒 Security Notes

1. **Never commit `.env` or `.env.production` files**
2. **Use strong passwords** for all services
3. **Enable SSL/HTTPS** in production
4. **Keep dependencies updated**: `pip list --outdated`
5. **Regular security audits**: `pip-audit`
6. **Backup database** regularly
7. **Monitor logs** for suspicious activity

---

## 📞 Support

For issues or questions:
- Check logs: `./dc.sh logs -f`
- Review troubleshooting section above
- Check Django documentation: https://docs.djangoproject.com/
- Docker documentation: https://docs.docker.com/

---

## 📄 License

[Add your license information here]

---

## 👥 Contributors

[Add contributor information here]
