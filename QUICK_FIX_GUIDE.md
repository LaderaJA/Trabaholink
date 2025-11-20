# 🔧 Quick Fix Guide - Docker Build Issue

## ✅ Issue Fixed!

The Dockerfile has been corrected. Now you need to rebuild.

---

## 🚀 Run These Commands:

```bash
cd Trabaholink

# Clean up any old containers
sudo docker-compose down

# Rebuild the Docker image (this will take 5-10 minutes)
sudo docker-compose build --no-cache

# Start all services
sudo docker-compose --env-file .env.docker up -d

# Wait for services to start (30 seconds)
sleep 30

# Check status
sudo docker-compose ps
```

---

## 📊 Expected Output:

After `sudo docker-compose ps`, you should see:

```
NAME                        STATUS
trabaholink_celery_beat     Up
trabaholink_celery_worker   Up
trabaholink_db              Up (healthy)
trabaholink_redis           Up (healthy)
trabaholink_web             Up
```

---

## ✅ Verify It's Working:

```bash
# Test health endpoint
curl http://localhost:8000/health/

# Expected response:
{"status":"healthy","service":"trabaholink"}

# View logs
sudo docker-compose logs -f web
```

---

## 🎯 Next Steps After Build Succeeds:

### 1. Test Basic Application
```bash
# Open in browser
http://localhost:8000

# Should see the Trabaholink homepage
```

### 2. Install Monitoring
```bash
sudo ./scripts/install-monitoring.sh

# Access Grafana
http://localhost:3000
Login: admin / admin
```

### 3. Install Logging
```bash
sudo ./scripts/install-logging.sh

# Configure in Grafana:
# Add data source → Loki → http://loki:3100
```

### 4. Real-time Monitoring
```bash
sudo ./scripts/monitor.sh

# Shows live service status
```

---

## 🐛 If Build Still Fails:

### Check Docker is Running:
```bash
sudo systemctl status docker
```

### Check Disk Space:
```bash
df -h
```

### View Build Logs:
```bash
sudo docker-compose build 2>&1 | tee build.log
```

### Clean Everything:
```bash
# Remove all containers and images
sudo docker-compose down -v
sudo docker system prune -a

# Rebuild from scratch
sudo docker-compose build
```

---

## 📝 What Was Fixed:

The issue was with the `COPY` command in the Dockerfile. Changed from:
```dockerfile
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
```

To:
```dockerfile
COPY entrypoint.sh /entrypoint.sh
```

This ensures the file is copied before we switch to the non-root user.

---

## ⏱️ Build Time:

First build: **5-10 minutes** (downloading all dependencies)
- Python packages
- System libraries (GDAL, PostGIS, OpenCV, dlib)
- Playwright browsers

Subsequent builds: **1-2 minutes** (cached layers)

---

## 🆘 Still Having Issues?

1. Copy the error message
2. Run: `sudo docker-compose logs web`
3. Share the output for help

---

## ✅ Success Checklist:

- [ ] Build completes without errors
- [ ] All 5 services show "Up" status
- [ ] Health endpoint responds
- [ ] Can access http://localhost:8000
- [ ] No errors in logs

---

**Ready to build? Run the commands above!** 🚀
