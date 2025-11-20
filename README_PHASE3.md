# 🚀 Phase 3: Advanced Features - Complete Guide

This guide covers advanced features including CI/CD, monitoring, logging, and Kubernetes deployment.

---

## 📋 Table of Contents

1. [CI/CD with GitHub Actions](#cicd-with-github-actions)
2. [Monitoring Stack (Prometheus + Grafana)](#monitoring-stack)
3. [Logging Stack (Loki + Promtail)](#logging-stack)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Helm Charts](#helm-charts)
6. [Performance Testing](#performance-testing)
7. [Security Scanning](#security-scanning)

---

## 🔄 CI/CD with GitHub Actions

### Overview

Automated build, test, and deployment pipeline using GitHub Actions.

### Workflows Included

#### 1. Docker Build and Push (`.github/workflows/docker-build.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests
- Version tags (e.g., `v1.0.0`)

**What it does:**
- ✅ Builds Docker image
- ✅ Runs security scan with Trivy
- ✅ Pushes to GitHub Container Registry
- ✅ Runs automated tests
- ✅ Performs health checks

**Setup:**

```bash
# 1. Enable GitHub Packages
# Go to Settings → Actions → General
# Enable "Read and write permissions"

# 2. Push code to trigger workflow
git push origin main

# 3. View workflow
# Go to Actions tab in GitHub
```

#### 2. Production Deployment (`.github/workflows/deploy-production.yml`)

**Triggers:**
- Manual workflow dispatch

**What it does:**
- ✅ Connects to production server via SSH
- ✅ Pulls latest code
- ✅ Runs deployment script
- ✅ Verifies deployment

**Setup:**

```bash
# 1. Add GitHub secrets
# Go to Settings → Secrets → Actions → New secret

SSH_PRIVATE_KEY   # Your SSH private key
SERVER_HOST       # e.g., trabaholink.com
SERVER_USER       # e.g., ubuntu
DEPLOY_PATH       # e.g., /home/ubuntu/trabaholink
DOMAIN           # e.g., trabaholink.com

# 2. Trigger deployment
# Go to Actions → Deploy to Production → Run workflow
```

### GitHub Actions Best Practices

- ✅ Always test in staging first
- ✅ Use environment protection rules
- ✅ Enable required reviewers for production
- ✅ Set up Slack/Discord notifications
- ✅ Monitor workflow run times

---

## 📊 Monitoring Stack

### Prometheus + Grafana Setup

**Components:**
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Node Exporter**: System metrics
- **cAdvisor**: Container metrics
- **Postgres Exporter**: Database metrics
- **Redis Exporter**: Cache metrics

### Installation

```bash
cd Trabaholink
./scripts/install-monitoring.sh
```

### Access Points

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| Node Exporter | http://localhost:9100 | - |
| cAdvisor | http://localhost:8080 | - |

### Grafana Setup

1. **Login to Grafana**
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: `admin` (change on first login)

2. **Data Source (Auto-configured)**
   - Prometheus is already connected
   - Verify at: Configuration → Data Sources

3. **Import Dashboards**

   Recommended dashboards from grafana.com:

   - **1860**: Node Exporter Full
     - Complete system metrics
     - CPU, Memory, Disk, Network

   - **893**: Docker & System Monitoring
     - Container resource usage
     - Docker-specific metrics

   - **3662**: Prometheus 2.0 Stats
     - Prometheus performance
     - Query stats

   - **7362**: PostgreSQL Database
     - Database connections
     - Query performance

   **To import:**
   - Click "+" → Import
   - Enter dashboard ID
   - Select Prometheus data source
   - Click Import

4. **Create Custom Dashboards**

   Example: Django Application Dashboard
   ```
   Panel: Request Rate
   Query: rate(django_http_requests_total[5m])
   
   Panel: Response Time (95th percentile)
   Query: histogram_quantile(0.95, django_http_requests_latency_seconds_bucket)
   
   Panel: Error Rate
   Query: rate(django_http_responses_total{status=~"5.."}[5m])
   ```

### Prometheus Alerts

Configured alerts in `monitoring/prometheus/alerts.yml`:

- 🔴 **Critical**: Application/Database/Redis down
- 🟡 **Warning**: High CPU/Memory/Disk usage
- 🟡 **Warning**: Slow HTTP responses
- 🟡 **Warning**: Celery queue backup

### Metrics Available

#### Application Metrics
- HTTP request rate and latency
- Response codes (2xx, 4xx, 5xx)
- Active connections
- Celery task metrics

#### System Metrics
- CPU usage and load
- Memory usage and swap
- Disk I/O and space
- Network traffic

#### Database Metrics
- Connection count
- Query performance
- Cache hit ratio
- Transaction rate

#### Container Metrics
- Container CPU/Memory
- Network I/O
- Disk I/O
- Restart count

---

## 📝 Logging Stack

### Loki + Promtail Setup

**Components:**
- **Loki**: Log aggregation and storage
- **Promtail**: Log collection agent
- **Grafana**: Log visualization

### Installation

```bash
cd Trabaholink
./scripts/install-logging.sh
```

### Configure Grafana for Logs

1. **Add Loki Data Source**
   - Go to Configuration → Data Sources
   - Click "Add data source"
   - Select "Loki"
   - URL: `http://loki:3100`
   - Click "Save & Test"

2. **Explore Logs**
   - Click "Explore" (compass icon)
   - Select "Loki" data source
   - Use LogQL queries

### LogQL Query Examples

```logql
# All web application logs
{container="trabaholink_web"}

# Error logs only
{container="trabaholink_web"} |= "ERROR"

# Database logs
{container="trabaholink_db"}

# Filter by time range
{service="web"} |= "error" [1h]

# Count errors per minute
sum(count_over_time({container="trabaholink_web"} |= "ERROR" [1m]))

# Slow queries
{container="trabaholink_db"} |~ "duration: [0-9]+ms" | duration > 1000

# 5xx errors in Nginx
{job="nginx"} |= "status=5"

# Celery task failures
{container="trabaholink_celery_worker"} |= "Task.*FAILURE"
```

### Log Retention

- Default: 30 days
- Configure in `logging/loki/loki-config.yml`
- Adjust based on compliance needs

---

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl installed and configured
- Ingress controller (nginx)
- cert-manager (for SSL)

### Deployment Methods

#### Method 1: Using kubectl + Kustomize

```bash
# Deploy to production namespace
cd Trabaholink/kubernetes/base
kubectl apply -k .

# Check status
kubectl get all -n trabaholink
```

#### Method 2: Using Deployment Script

```bash
cd Trabaholink
./scripts/kubernetes/deploy-k8s.sh

# Select environment (dev/staging/prod)
# Script handles everything
```

### Kubernetes Resources Created

- **Deployments**: web, celery-worker, celery-beat
- **Services**: web, postgres, redis
- **Ingress**: SSL-enabled with Let's Encrypt
- **PVCs**: static files, media files, database, cache
- **Secrets**: database credentials, Django secret key
- **ConfigMaps**: application configuration

### Scaling

```bash
# Scale web pods
kubectl scale deployment trabaholink-web -n trabaholink --replicas=5

# Scale celery workers
kubectl scale deployment trabaholink-celery-worker -n trabaholink --replicas=4

# Enable autoscaling
kubectl autoscale deployment trabaholink-web -n trabaholink \
  --cpu-percent=80 --min=2 --max=10
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/trabaholink-web \
  trabaholink=trabaholink:v2.0.0 -n trabaholink

# Check rollout status
kubectl rollout status deployment/trabaholink-web -n trabaholink

# Rollback if needed
./scripts/kubernetes/rollback-k8s.sh
```

### Monitoring in Kubernetes

```bash
# View logs
kubectl logs -f deployment/trabaholink-web -n trabaholink

# Execute commands
kubectl exec -it deployment/trabaholink-web -n trabaholink -- python manage.py shell

# Port forward for local access
kubectl port-forward svc/trabaholink-web 8000:8000 -n trabaholink
```

---

## ⛵ Helm Charts

### What is Helm?

Helm is a package manager for Kubernetes that simplifies deployment and management.

### Install Helm

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Deploy with Helm

```bash
cd Trabaholink/helm

# Install (first time)
helm install trabaholink ./trabaholink \
  --namespace trabaholink \
  --create-namespace \
  --values ./trabaholink/values.yaml

# Upgrade (updates)
helm upgrade trabaholink ./trabaholink \
  --namespace trabaholink

# Rollback
helm rollback trabaholink 1 --namespace trabaholink

# Uninstall
helm uninstall trabaholink --namespace trabaholink
```

### Customize Values

Create `values-production.yaml`:

```yaml
replicaCount: 5

image:
  repository: ghcr.io/your-org/trabaholink
  tag: "v1.2.0"

ingress:
  hosts:
    - host: trabaholink.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
```

Deploy with custom values:

```bash
helm install trabaholink ./trabaholink \
  --namespace trabaholink \
  --values values-production.yaml
```

---

## ⚡ Performance Testing

### Apache Bench Testing

```bash
cd Trabaholink
./scripts/performance-test.sh

# Follow prompts:
# - Target URL: http://localhost:8000/
# - Requests: 10000
# - Concurrency: 100
```

### Interpreting Results

Key metrics:
- **Requests per second**: Higher is better
- **Time per request**: Lower is better
- **Failed requests**: Should be 0
- **Transfer rate**: Network throughput

Example output:
```
Requests per second:    1234.56 [#/sec]
Time per request:       8.100 [ms] (mean)
Time per request:       0.081 [ms] (mean, across all concurrent requests)
Failed requests:        0
```

### Load Testing with k6 (Optional)

```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.45.0/k6-v0.45.0-linux-amd64.tar.gz -L | tar xvz
sudo mv k6-v0.45.0-linux-amd64/k6 /usr/local/bin/

# Create test script
cat > load-test.js << 'EOF'
import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  http.get('http://localhost:8000/');
  sleep(1);
}
EOF

# Run test
k6 run load-test.js
```

---

## 🔐 Security Scanning

### Trivy Security Scanner

```bash
cd Trabaholink
./scripts/security-scan.sh
```

**What it scans:**
- ✅ OS packages (Alpine/Ubuntu)
- ✅ Python packages (pip)
- ✅ Known vulnerabilities (CVE database)
- ✅ Misconfigurations

**Severity Levels:**
- 🔴 **CRITICAL**: Immediate action required
- 🟠 **HIGH**: Should be addressed soon
- 🟡 **MEDIUM**: Consider addressing
- 🔵 **LOW**: Informational

### CI/CD Integration

Security scanning is automatically run in the GitHub Actions workflow on every push.

### Fixing Vulnerabilities

1. **Update base image**
   ```dockerfile
   FROM python:3.11-slim-bookworm  # Use latest patch version
   ```

2. **Update Python packages**
   ```bash
   pip install --upgrade package-name
   ```

3. **Rebuild image**
   ```bash
   docker-compose build --no-cache
   ```

---

## 🎯 Phase 3 Features Summary

| Feature | Status | Description |
|---------|--------|-------------|
| CI/CD Pipeline | ✅ | Automated build, test, deploy |
| Monitoring | ✅ | Prometheus + Grafana |
| Logging | ✅ | Loki + Promtail |
| Alerting | ✅ | Prometheus alerts |
| Kubernetes | ✅ | Production-ready manifests |
| Helm Charts | ✅ | Package manager deployment |
| Performance Testing | ✅ | Apache Bench + k6 |
| Security Scanning | ✅ | Trivy vulnerability scanning |
| Auto-scaling | ✅ | HPA for Kubernetes |
| Health Checks | ✅ | Liveness & readiness probes |

---

## 📊 Architecture Diagram

```
                    Internet
                       |
                   [Ingress]
                   (SSL/TLS)
                       |
        +--------------+--------------+
        |              |              |
    [Web Pods]    [Celery Pods]  [Beat Pod]
    (Replicas)    (Replicas)     (Singleton)
        |              |              |
        +-------+------+------+-------+
                |             |
            [Redis]      [PostgreSQL]
            (Cache)      (Database)
                |             |
        [PersistentVolumes]   |
                              |
                    +-----Monitoring-----+
                    |                    |
              [Prometheus]          [Grafana]
                    |                    |
              [Exporters]            [Loki]
                                        |
                                  [Promtail]
```

---

## 🚀 Quick Start Commands

```bash
# Install monitoring
./scripts/install-monitoring.sh

# Install logging
./scripts/install-logging.sh

# Deploy to Kubernetes
./scripts/kubernetes/deploy-k8s.sh

# Run performance test
./scripts/performance-test.sh

# Run security scan
./scripts/security-scan.sh

# Deploy with Helm
helm install trabaholink ./helm/trabaholink
```

---

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)

---

## 🆘 Troubleshooting

### Monitoring Issues

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana logs
docker-compose logs grafana

# Restart monitoring
docker-compose restart prometheus grafana
```

### Kubernetes Issues

```bash
# Check pod status
kubectl get pods -n trabaholink

# View pod logs
kubectl logs -f <pod-name> -n trabaholink

# Describe pod for events
kubectl describe pod <pod-name> -n trabaholink

# Check ingress
kubectl describe ingress -n trabaholink
```

### CI/CD Issues

```bash
# View workflow logs in GitHub Actions tab

# Re-run failed workflow
# GitHub → Actions → Select workflow → Re-run jobs

# Check secrets are configured
# GitHub → Settings → Secrets → Actions
```

---

**Phase 3 Complete!** 🎉 You now have an enterprise-grade, fully-monitored, auto-scaling infrastructure!
