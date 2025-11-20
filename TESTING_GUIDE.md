# 🧪 Docker Setup Testing Guide

This guide walks you through testing all Docker features.

---

## ⚠️ Prerequisites

### Docker Permissions

You need to either:

**Option 1: Add user to docker group (recommended)**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Option 2: Use sudo with all docker commands**
```bash
sudo docker-compose ...
```

---

## 🎯 Testing Steps

### Step 1: Basic Application

```bash
cd Trabaholink

# Start basic stack
sudo docker-compose --env-file .env.docker up -d

# Wait 30 seconds for services to initialize
sleep 30

# Check status
sudo docker-compose ps

# All services should show "Up"
```

**Test Health Endpoint:**
```bash
curl http://localhost:8000/health/
# Expected: {"status":"healthy","service":"trabaholink"}
```

**View Logs:**
```bash
sudo docker-compose logs -f web
# Press Ctrl+C to exit
```

**Access Application:**
- Web: http://localhost:8000
- Admin: http://localhost:8000/admin

---

### Step 2: Monitoring Stack

```bash
# Install monitoring
sudo ./scripts/install-monitoring.sh
```

**Access Points:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Node Exporter: http://localhost:9100
- cAdvisor: http://localhost:8080

**Test Grafana:**

1. Open http://localhost:3000
2. Login: admin / admin
3. Change password
4. Go to Explore (compass icon)
5. Select "Prometheus" data source
6. Try query: `up`
7. Should see all services = 1 (up)

**Import Dashboard:**

1. Click "+" → Import
2. Enter ID: `1860`
3. Click "Load"
4. Select "Prometheus" data source
5. Click "Import"
6. View Node Exporter Full dashboard

**Check Prometheus Targets:**
- Open http://localhost:9090/targets
- All targets should be "UP"

---

### Step 3: Logging Stack

```bash
# Install logging
sudo ./scripts/install-logging.sh
```

**Configure Loki in Grafana:**

1. Open Grafana: http://localhost:3000
2. Go to Configuration → Data Sources
3. Click "Add data source"
4. Select "Loki"
5. URL: `http://loki:3100`
6. Click "Save & Test" (should show success)

**View Logs:**

1. Go to Explore
2. Select "Loki" data source
3. Try queries:

```logql
# All web application logs
{container="trabaholink_web"}

# Error logs only
{container="trabaholink_web"} |= "ERROR"

# Database logs
{container="trabaholink_db"}

# Celery worker logs
{container="trabaholink_celery_worker"}

# Last 5 minutes of logs
{service="web"} [5m]
```

---

### Step 4: Real-time Monitoring

```bash
# Start monitor dashboard
sudo ./scripts/monitor.sh
```

**What you'll see:**
- Service status (all should be "Up")
- Resource usage (CPU, Memory, Network)
- Health checks (all should be "Healthy")
- Recent logs

Press Ctrl+C to exit.

---

### Step 5: Full Stack Test

```bash
# Start everything together
sudo docker-compose \
  -f docker-compose.yml \
  -f docker-compose.monitoring.yml \
  -f docker-compose.logging.yml \
  --env-file .env.docker up -d

# Check all services
sudo docker-compose ps

# Should see:
# - web, db, redis, celery_worker, celery_beat
# - prometheus, grafana, node_exporter, cadvisor
# - postgres_exporter, redis_exporter
# - loki, promtail
```

---

## 📊 What to Test

### Application Functionality

- [ ] Health endpoint responds: `curl http://localhost:8000/health/`
- [ ] Home page loads: http://localhost:8000
- [ ] Admin panel loads: http://localhost:8000/admin
- [ ] Static files load correctly

### Monitoring

- [ ] Grafana loads at :3000
- [ ] Can login to Grafana
- [ ] Prometheus data source is configured
- [ ] Can run Prometheus queries
- [ ] Dashboard imported successfully
- [ ] Dashboard shows live data
- [ ] All Prometheus targets are UP

### Logging

- [ ] Loki data source configured
- [ ] Can view container logs
- [ ] Can filter logs by container
- [ ] Can search for specific log entries
- [ ] Logs update in real-time

### Performance

- [ ] All services start within 60 seconds
- [ ] Health checks pass consistently
- [ ] No services in "Restarting" state
- [ ] Resource usage is reasonable

---

## 🔍 Verification Commands

```bash
# Check service status
sudo docker-compose ps

# Check container resource usage
sudo docker stats

# Check logs for errors
sudo docker-compose logs | grep -i error

# Check health endpoint
curl http://localhost:8000/health/
curl http://localhost:8000/health/detailed/

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# Check Loki is running
curl http://localhost:3100/ready

# Test database connection
sudo docker-compose exec db psql -U postgres -d trabaholink -c "SELECT 1;"

# Test Redis connection
sudo docker-compose exec redis redis-cli ping
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check logs
sudo docker-compose logs <service-name>

# Rebuild without cache
sudo docker-compose build --no-cache

# Remove and recreate
sudo docker-compose down -v
sudo docker-compose up -d
```

### Port Conflicts

```bash
# Check what's using a port
sudo netstat -tlnp | grep <port>

# Kill process using port
sudo kill -9 <PID>

# Or change port in .env.docker
```

### Permission Errors

```bash
# Fix volume permissions
sudo docker-compose exec web chown -R appuser:appuser /app
```

### Health Check Fails

```bash
# Check if services are ready
sudo docker-compose exec db pg_isready -U postgres
sudo docker-compose exec redis redis-cli ping

# Check application logs
sudo docker-compose logs web

# Try manual health check
curl -v http://localhost:8000/health/
```

### Grafana Can't Connect to Prometheus

```bash
# Check Prometheus is running
sudo docker-compose ps prometheus

# Check Prometheus logs
sudo docker-compose logs prometheus

# Verify network
sudo docker network ls
sudo docker network inspect trabaholink_trabaholink_network
```

---

## 🎯 Success Criteria

Your setup is working correctly if:

✅ All services show "Up" status  
✅ Health endpoint returns healthy  
✅ Grafana loads and shows data  
✅ Prometheus targets are all UP  
✅ Loki shows container logs  
✅ Monitor script shows all healthy  
✅ No errors in container logs  
✅ Can import and view dashboards  
✅ Logs update in real-time  
✅ Resource usage is stable  

---

## 📸 Document Your Results

Take screenshots of:

1. `docker-compose ps` output (all services Up)
2. Health endpoint JSON response
3. Grafana dashboard showing metrics
4. Grafana Explore showing logs
5. Prometheus targets page (all UP)
6. Monitor script output

---

## 🧹 Cleanup

### Stop All Services
```bash
sudo docker-compose down
```

### Stop and Remove Data
```bash
sudo docker-compose down -v
```

### Remove Monitoring/Logging
```bash
sudo docker-compose -f docker-compose.yml \
  -f docker-compose.monitoring.yml \
  -f docker-compose.logging.yml down
```

---

## 📚 Next Steps After Testing

Once everything works:

1. **Production Deployment**: Follow README_PRODUCTION.md
2. **Setup CI/CD**: Configure GitHub Actions secrets
3. **Kubernetes**: Try `./scripts/kubernetes/deploy-k8s.sh`
4. **Performance Testing**: Run `./scripts/performance-test.sh`
5. **Security Scan**: Run `./scripts/security-scan.sh`

---

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `sudo docker-compose logs -f`
2. Review health: `curl http://localhost:8000/health/detailed/`
3. Check Docker: `sudo docker info`
4. Verify network: `sudo docker network ls`
5. Check resources: `sudo docker stats`

---

**Happy Testing! 🎉**
