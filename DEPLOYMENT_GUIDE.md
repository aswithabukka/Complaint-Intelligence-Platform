# Production Deployment Guide

## 📋 Prerequisites

### Required Tools
```bash
# Install required tools
brew install terraform       # Infrastructure as Code
brew install kubectl         # Kubernetes CLI
brew install helm           # Kubernetes package manager
brew install aws-cli        # AWS CLI
brew install docker         # Container runtime
brew install k9s            # Kubernetes TUI (optional but recommended)
```

### Required Accounts & Access
- [x] AWS Account with admin access
- [x] GitHub account with repository access
- [x] OpenAI API Key
- [x] Docker Hub / GCR account
- [x] Datadog / New Relic account (optional)
- [x] Sentry account for error tracking (optional)

## 🚀 Deployment Steps

### Step 1: Infrastructure Setup with Terraform

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
aws_region     = "us-east-1"
environment    = "prod"
project_name   = "complaint-platform"
cluster_name   = "complaint-platform-cluster"
vpc_cidr       = "10.0.0.0/16"
EOF

# Plan infrastructure changes
terraform plan -out=tfplan

# Review the plan carefully
# Apply infrastructure changes
terraform apply tfplan

# This will create:
# - VPC with public/private subnets across 3 AZs
# - EKS cluster with 2 node groups
# - RDS PostgreSQL Multi-AZ
# - ElastiCache Redis cluster
# - S3 bucket with lifecycle policies
# - KMS keys for encryption
# - Security groups and IAM roles
```

**Estimated time**: 20-30 minutes

### Step 2: Configure kubectl

```bash
# Get EKS cluster credentials
aws eks update-kubeconfig \\
  --region us-east-1 \\
  --name complaint-platform-cluster

# Verify connection
kubectl get nodes

# Expected output:
# NAME                           STATUS   ROLES    AGE   VERSION
# ip-10-0-1-123.ec2.internal     Ready    <none>   5m    v1.28.x
# ip-10-0-2-124.ec2.internal     Ready    <none>   5m    v1.28.x
# ip-10-0-3-125.ec2.internal     Ready    <none>   5m    v1.28.x
```

### Step 3: Install Kubernetes Add-ons

#### Install NGINX Ingress Controller
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \\
  --namespace ingress-nginx \\
  --create-namespace \\
  --set controller.service.type=LoadBalancer \\
  --set controller.metrics.enabled=true \\
  --set controller.podAnnotations."prometheus\\.io/scrape"=true
```

#### Install Cert-Manager (for SSL)
```bash
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \\
  --namespace cert-manager \\
  --create-namespace \\
  --set installCRDs=true
```

#### Install Prometheus + Grafana
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \\
  --namespace monitoring \\
  --create-namespace \\
  --set prometheus.prometheusSpec.retention=30d \\
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=100Gi \\
  --set grafana.adminPassword='<STRONG_PASSWORD>'
```

#### Install ELK Stack (Elasticsearch, Logstash, Kibana)
```bash
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch \\
  --namespace logging \\
  --create-namespace \\
  --set replicas=3 \\
  --set resources.requests.memory=2Gi

helm install kibana elastic/kibana \\
  --namespace logging \\
  --set resources.requests.memory=1Gi
```

### Step 4: Create Kubernetes Secrets

```bash
# Database credentials
kubectl create secret generic database-secrets \\
  --from-literal=url="postgresql://user:pass@<RDS_ENDPOINT>:5432/complaints"

# AWS credentials for S3
kubectl create secret generic aws-secrets \\
  --from-literal=access_key_id="<AWS_ACCESS_KEY>" \\
  --from-literal=secret_access_key="<AWS_SECRET_KEY>"

# OpenAI API key
kubectl create secret generic api-secrets \\
  --from-literal=openai_api_key="<OPENAI_API_KEY>"

# Redis auth token (from Terraform output)
kubectl create secret generic redis-secrets \\
  --from-literal=auth_token="<REDIS_AUTH_TOKEN>"
```

### Step 5: Create ConfigMaps

```bash
# Application configuration
kubectl apply -f k8s/base/configmap.yaml

# Update with actual values
kubectl edit configmap app-config

# Update these values:
# - redis_url: "redis://<REDIS_ENDPOINT>:6379/0"
# - s3_bucket: "complaint-platform-documents-prod"
# - api_url: "https://api.complaint-platform.com"
```

### Step 6: Deploy Application

```bash
# Apply base Kubernetes manifests
kubectl apply -f k8s/base/api-deployment.yaml
kubectl apply -f k8s/base/worker-deployment.yaml
kubectl apply -f k8s/base/frontend-deployment.yaml
kubectl apply -f k8s/base/ingress.yaml

# Verify deployments
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get ingress

# Check pod logs
kubectl logs -f deployment/api
kubectl logs -f deployment/worker
kubectl logs -f deployment/frontend
```

### Step 7: Run Database Migrations

```bash
# Get API pod name
API_POD=$(kubectl get pod -l app=api -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec $API_POD -- alembic upgrade head

# Verify migration
kubectl exec $API_POD -- alembic current
```

### Step 8: Configure DNS

```bash
# Get Load Balancer endpoint
kubectl get ingress complaint-platform-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Output example:
# a1b2c3d4-1234567890.us-east-1.elb.amazonaws.com

# In your DNS provider (Route53, Cloudflare, etc.), create:
# A/CNAME record: complaint-platform.com -> <LB_HOSTNAME>
# A/CNAME record: api.complaint-platform.com -> <LB_HOSTNAME>
```

### Step 9: Setup CI/CD

#### Configure GitHub Secrets

Go to GitHub Repository → Settings → Secrets and add:

```
GCP_SA_KEY          # Google Cloud service account key (JSON)
SNYK_TOKEN          # Snyk API token
SONAR_TOKEN         # SonarCloud token
SLACK_WEBHOOK       # Slack webhook URL
K6_CLOUD_TOKEN      # k6 cloud token
AWS_ACCESS_KEY_ID   # AWS credentials
AWS_SECRET_ACCESS_KEY
```

#### Enable GitHub Actions

```bash
# Push changes to main branch
git add .
git commit -m "feat: Add production deployment"
git push origin main

# GitHub Actions will automatically:
# 1. Run security scans
# 2. Run tests
# 3. Build Docker images
# 4. Scan images for vulnerabilities
# 5. Deploy to Kubernetes
# 6. Run smoke tests
```

### Step 10: Configure Monitoring

#### Access Grafana
```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Open http://localhost:3000
# Login: admin / <password-from-step-3>

# Import dashboards:
# - Kubernetes Cluster Monitoring (ID: 7249)
# - PostgreSQL Database (ID: 9628)
# - Redis Dashboard (ID: 11835)
# - NGINX Ingress (ID: 9614)
```

#### Access Kibana
```bash
# Port forward Kibana
kubectl port-forward -n logging svc/kibana 5601:5601

# Open http://localhost:5601
# Create index pattern: logs-*
# Explore logs from all services
```

#### Configure Alerts

```bash
# Create AlertManager configuration
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      slack_api_url: '<SLACK_WEBHOOK_URL>'

    route:
      receiver: 'slack-notifications'
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 5m
      repeat_interval: 3h

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#alerts'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        title: '{{ .GroupLabels.alertname }}'
EOF
```

## 🔐 Security Hardening

### Enable Pod Security Standards
```bash
kubectl label namespace default pod-security.kubernetes.io/enforce=restricted
```

### Network Policies
```bash
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-db
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
EOF
```

### Enable Audit Logging
```bash
# Configure EKS audit logs
aws eks update-cluster-config \\
  --region us-east-1 \\
  --name complaint-platform-cluster \\
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

## 📊 Performance Optimization

### Configure Autoscaling
```bash
# Cluster Autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \\
  --set autoDiscovery.clusterName=complaint-platform-cluster \\
  --set awsRegion=us-east-1
```

### Enable Caching
```bash
# Redis caching is already configured
# Verify Redis connection from API pod
API_POD=$(kubectl get pod -l app=api -o jsonpath='{.items[0].metadata.name}')
kubectl exec $API_POD -- redis-cli -h <REDIS_ENDPOINT> PING
# Expected: PONG
```

## 🔄 Backup & Disaster Recovery

### Database Backups
```bash
# RDS automated backups are enabled (30-day retention)
# Manual snapshot
aws rds create-db-snapshot \\
  --db-instance-identifier complaint-platform-db \\
  --db-snapshot-identifier complaint-platform-manual-$(date +%Y%m%d)
```

### S3 Versioning
```bash
# S3 versioning is enabled via Terraform
# Verify versioning
aws s3api get-bucket-versioning --bucket complaint-platform-documents-prod
```

### Kubernetes Backup with Velero
```bash
helm install velero vmware-tanzu/velero \\
  --namespace velero \\
  --create-namespace \\
  --set configuration.provider=aws \\
  --set configuration.backupStorageLocation.bucket=complaint-platform-backups \\
  --set configuration.backupStorageLocation.config.region=us-east-1

# Create backup schedule
velero schedule create daily-backup --schedule="0 2 * * *"
```

## 🧪 Testing

### Smoke Tests
```bash
# API health check
curl https://api.complaint-platform.com/health

# Frontend
curl https://complaint-platform.com

# Create test complaint
curl -X POST https://api.complaint-platform.com/api/v1/complaints \\
  -H "Content-Type: application/json" \\
  -d '{"title":"Test Complaint","description":"Testing production deployment"}'
```

### Load Testing
```bash
# Using k6
k6 run tests/performance/load-test.js

# Expected results:
# - p95 latency < 200ms
# - Error rate < 1%
# - Throughput > 1000 req/s
```

## 📈 Monitoring Checklist

- [ ] Grafana dashboards configured
- [ ] Prometheus alerts configured
- [ ] ELK stack receiving logs
- [ ] Sentry error tracking configured
- [ ] Uptime monitoring (Pingdom/UptimeRobot)
- [ ] SSL certificate renewal (automatic via cert-manager)
- [ ] Database monitoring enabled
- [ ] Redis monitoring enabled

## 💰 Cost Monitoring

```bash
# Enable AWS Cost Explorer
# Set budget alerts
aws budgets create-budget \\
  --account-id <ACCOUNT_ID> \\
  --budget file://budget.json

# Tag all resources for cost allocation
# Monitor spending by:
# - Environment (prod/dev)
# - Service (EKS/RDS/S3)
# - Team
```

## 🆘 Troubleshooting

### Pod not starting
```bash
kubectl describe pod <POD_NAME>
kubectl logs <POD_NAME>
kubectl get events --sort-by='.lastTimestamp'
```

### Database connection issues
```bash
# Check security groups
# Verify RDS endpoint
# Test connection from API pod
kubectl exec -it <API_POD> -- psql $DATABASE_URL
```

### High memory usage
```bash
# Check pod metrics
kubectl top pods

# Increase resource limits if needed
kubectl edit deployment api
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Prometheus Operator](https://prometheus-operator.dev/)

---

**Deployment Time**: ~2-3 hours for initial setup
**Maintenance**: Automated with CI/CD
**Support**: DevOps team available 24/7

🎉 **Congratulations! Your production deployment is complete!**
