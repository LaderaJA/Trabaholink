# 🔄 Docker Setup Comparison Guide

This guide helps you choose between different Docker configurations for Trabaholink.

---

## 📊 Configuration Comparison

| Feature | Phase 1 (Basic) | Phase 2 Dev | Phase 2 Production |
|---------|----------------|-------------|-------------------|
| **Command** | `docker-compose up -d` | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d` | Same + `--env-file .env.production` |
| **Reverse Proxy** | ❌ No | ✅ Nginx | ✅ Nginx |
| **SSL/TLS** | ❌ No | ⚠️ Self-signed | ✅ Let's Encrypt |
| **HTTPS** | ❌ No | ⚠️ Warning in browser | ✅ Valid certificate |
| **Web Port** | 8000 (exposed) | 80/443 (Nginx) | 80/443 (Nginx) |
| **Database** | 5432 (exposed) | 5432 (exposed) | ❌ Not exposed |
| **Redis** | 6379 (exposed) | 6379 (exposed) | ❌ Not exposed |
| **Static Files** | Django serves | Nginx serves | Nginx serves |
| **Caching** | Basic | 30-day | 30-day |
| **Compression** | ❌ No | ✅ Gzip | ✅ Gzip |
| **Security Headers** | ❌ No | ✅ Yes | ✅ Yes |
| **Resource Limits** | ❌ Unlimited | ❌ Unlimited | ✅ Limited |
| **Logging** | Basic | Basic | ✅ Rotation |
| **Auto-restart** | unless-stopped | unless-stopped | ✅ always |
| **Best For** | Quick testing | Team development | Production use |

---

## 🎯 Which Setup Should I Use?

### Use Phase 1 (Basic) When:
- 🧪 Just testing Docker for the first time
- 💻 Solo development on your laptop
- 🚀 Want fastest startup
- 📝 Don't need SSL
- 🔓 Okay with exposed ports

**Command:**
```bash
docker-compose --env-file .env.docker up -d
```

**Access:** http://localhost:8000

---

### Use Phase 2 Dev When:
- 👥 Team development environment
- 🌐 Testing with real-like production setup
- 🔐 Need to test SSL/HTTPS locally
- 📊 Want Nginx features (caching, compression)
- 🧪 Testing reverse proxy configuration

**Command:**
```bash
# Generate self-signed cert first
./scripts/generate-ssl-cert.sh

# Start with Nginx
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.docker up -d
```

**Access:** 
- http://localhost (redirects to HTTPS)
- https://localhost (browser SSL warning - ignore it)

---

### Use Phase 2 Production When:
- 🌍 Deploying to real server
- 🔒 Need valid SSL certificate
- 🚀 Production traffic
- 🛡️ Security is critical
- 📈 Need monitoring and backups

**Command:**
```bash
# First time setup
cp .env.production.example .env.production
# Edit .env.production
sudo ./scripts/setup-letsencrypt.sh
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# Subsequent deployments
./scripts/deploy.sh
```

**Access:** https://yourdomain.com

---

## 🔀 Migration Path

### From Phase 1 → Phase 2 Dev

```bash
# Stop Phase 1
docker-compose down

# Generate self-signed cert
./scripts/generate-ssl-cert.sh

# Start Phase 2 with same data
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.docker up -d
```

**Note:** Data is preserved (same volumes used)

---

### From Phase 2 Dev → Phase 2 Production

```bash
# 1. Create production config
cp .env.production.example .env.production
nano .env.production  # Update all values!

# 2. Backup database
./scripts/backup-database.sh

# 3. Stop dev environment
docker-compose down

# 4. Get real SSL certificate
sudo ./scripts/setup-letsencrypt.sh

# 5. Start production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
```

**Important:** Update DNS to point to your server before step 4!

---

### From Phase 1 → Phase 2 Production (Direct)

```bash
# 1. Backup current database
docker-compose exec -T db pg_dump -U postgres trabaholink > backup.sql

# 2. Stop Phase 1
docker-compose down

# 3. Setup production
cp .env.production.example .env.production
nano .env.production  # Update!

# 4. Get SSL certificate
sudo ./scripts/setup-letsencrypt.sh

# 5. Start production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# 6. Restore data if needed
docker-compose exec -T db psql -U postgres trabaholink < backup.sql
```

---

## 📁 File Usage by Configuration

### Phase 1 Files
```
Dockerfile
docker-compose.yml
.env.docker
entrypoint.sh
.dockerignore
```

### Phase 2 Dev Files (Additional)
```
nginx/nginx.dev.conf          ← Used automatically
nginx/Dockerfile
nginx/docker-entrypoint.sh
nginx/ssl/cert.pem            ← Self-signed
nginx/ssl/key.pem             ← Self-signed
docker-compose.prod.yml
```

### Phase 2 Production Files (Additional)
```
nginx/nginx.conf              ← Used automatically
.env.production
certbot/conf/                 ← Let's Encrypt certs
certbot/www/                  ← Verification
scripts/setup-letsencrypt.sh
scripts/deploy.sh
scripts/backup-database.sh
scripts/restore-database.sh
scripts/monitor.sh
```

---

## 🌐 URL Access Patterns

### Phase 1 (Basic)
```
http://localhost:8000/          → Django (Daphne)
http://localhost:8000/admin     → Django Admin
http://localhost:8000/static/   → Django static handler
http://localhost:8000/media/    → Django media handler
http://localhost:8000/ws/       → WebSocket (Channels)
```

### Phase 2 (All)
```
http://localhost/ or http://yourdomain.com/
    ↓ (Redirects to HTTPS)
https://localhost/ or https://yourdomain.com/
    → Nginx → Django

https://yourdomain.com/static/  → Nginx (cached 30 days)
https://yourdomain.com/media/   → Nginx (cached 7 days)
https://yourdomain.com/ws/      → Nginx → WebSocket upgrade
https://yourdomain.com/admin    → Nginx → Django Admin
```

---

## 🔧 Port Usage

| Port | Phase 1 | Phase 2 Dev | Phase 2 Prod |
|------|---------|-------------|--------------|
| 80 (HTTP) | ❌ | ✅ Nginx | ✅ Nginx |
| 443 (HTTPS) | ❌ | ✅ Nginx | ✅ Nginx |
| 8000 (Django) | ✅ Exposed | ❌ Internal | ❌ Internal |
| 5432 (PostgreSQL) | ✅ Exposed | ✅ Exposed | ❌ Internal |
| 6379 (Redis) | ✅ Exposed | ✅ Exposed | ❌ Internal |

**Security Note:** Phase 2 Production only exposes ports 80 and 443, making it more secure.

---

## 🎓 Common Scenarios

### Scenario 1: Local Development
**Use:** Phase 1 Basic
```bash
docker-compose --env-file .env.docker up -d
```
✅ Fastest, simplest, direct access

---

### Scenario 2: Testing HTTPS Features
**Use:** Phase 2 Dev
```bash
./scripts/generate-ssl-cert.sh
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
✅ Test SSL/HTTPS without real certificate

---

### Scenario 3: Staging Server
**Use:** Phase 2 Production
```bash
cp .env.production.example .env.staging
# Edit .env.staging
./scripts/generate-ssl-cert.sh  # Or use Let's Encrypt
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.staging up -d
```
✅ Production-like environment for testing

---

### Scenario 4: Production Server
**Use:** Phase 2 Production + Let's Encrypt
```bash
cp .env.production.example .env.production
# Edit with production values
sudo ./scripts/setup-letsencrypt.sh
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
```
✅ Full security, valid SSL, ready for users

---

## 🔄 Switching Between Configurations

### Switch from Basic to Dev
```bash
docker-compose down
./scripts/generate-ssl-cert.sh
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Switch from Dev to Basic
```bash
docker-compose down
docker-compose up -d
```

### Switch from Dev to Production
```bash
docker-compose down
sudo ./scripts/setup-letsencrypt.sh
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
```

**Note:** All configurations share the same data volumes, so your database and files persist!

---

## 🛡️ Security Comparison

| Security Feature | Phase 1 | Phase 2 Dev | Phase 2 Prod |
|-----------------|---------|-------------|--------------|
| Encrypted traffic | ❌ | ⚠️ Self-signed | ✅ Valid SSL |
| Exposed services | ⚠️ 3 ports | ⚠️ 3 ports | ✅ 2 ports only |
| HSTS headers | ❌ | ✅ | ✅ |
| XSS protection | Basic | ✅ Enhanced | ✅ Enhanced |
| CSRF protection | Django only | Django + Nginx | Django + Nginx |
| Resource limits | ❌ | ❌ | ✅ |
| Production grade | ❌ | ⚠️ Testing only | ✅ Yes |

---

## 📊 Performance Comparison

| Performance | Phase 1 | Phase 2 |
|------------|---------|---------|
| Static file serving | Django (slow) | Nginx (fast) |
| Compression | ❌ No | ✅ Gzip 60% savings |
| Browser caching | Minimal | 30 days |
| Connection pooling | Basic | Nginx + Django |
| Concurrent connections | ~100 | ~10,000 |

---

## 💰 Cost Implications

### Development (Local)
- **Phase 1:** Free, no overhead
- **Phase 2 Dev:** Free, slightly more RAM usage

### Production (Cloud Server)
- **Basic:** $5-10/month (DigitalOcean Droplet, 1GB RAM)
- **Recommended:** $20-40/month (4GB RAM, 2 CPU)
- **High Traffic:** $40-80/month (8GB RAM, 4 CPU)

**SSL Costs:** FREE with Let's Encrypt!

---

## 🎯 Decision Matrix

Ask yourself:

1. **Are you deploying to production?**
   - No → Phase 1
   - Yes → Phase 2 Production

2. **Do you need HTTPS for testing?**
   - No → Phase 1
   - Yes → Phase 2 Dev

3. **Are you working in a team?**
   - No → Phase 1
   - Yes → Phase 2 Dev

4. **Do you need monitoring/backups?**
   - No → Phase 1
   - Yes → Phase 2

5. **Is security critical?**
   - Not yet → Phase 1
   - Yes → Phase 2 Production

---

## 📚 Quick Command Reference

### Phase 1 (Basic)
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f
```

### Phase 2 (Dev/Prod)
```bash
# Start Dev
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Start Prod
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# Deploy (after first setup)
./scripts/deploy.sh

# Monitor
./scripts/monitor.sh

# Backup
./scripts/backup-database.sh
```

---

## ✅ Recommendation Summary

| Use Case | Recommended Configuration |
|----------|--------------------------|
| Solo development | Phase 1 Basic |
| Team development | Phase 2 Dev |
| Staging environment | Phase 2 Production (self-signed) |
| Production deployment | Phase 2 Production (Let's Encrypt) |
| Quick demo | Phase 1 Basic |
| Client presentation | Phase 2 Dev or Production |

---

**Still unsure?** Start with **Phase 1** for learning, then upgrade to **Phase 2** when you're ready to deploy!

**Questions?** Check the relevant documentation:
- Phase 1: `README_DOCKER.md`
- Phase 2: `README_PRODUCTION.md`
