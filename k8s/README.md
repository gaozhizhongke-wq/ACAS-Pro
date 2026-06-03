# ACAS Pro - Kubernetes Deployment

## 🚀 Quick Start

### 1. Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.x (optional)
- cert-manager (for SSL)
- nginx-ingress (for load balancing)

### 2. Deploy with Kubectl

```bash
# Create namespace
kubectl create namespace acas-pro

# Apply manifests
kubectl apply -f k8s/01-deployment.yaml

# Verify deployment
kubectl get pods -n acas-pro
kubectl get svc -n acas-pro
kubectl get ingress -n acas-pro
```

### 3. Deploy with Helm

```bash
# Add dependencies
helm dependency update helm/acas-pro

# Install chart
helm install acas-pro helm/acas-pro \
  --namespace acas-pro \
  --create-namespace \
  --set ingress.hosts[0].host=your-domain.com \
  --set secrets.SECRET_KEY=$(openssl rand -hex 32) \
  --set secrets.DEEPSEEK_API_KEY=your-api-key

# Upgrade
helm upgrade acas-pro helm/acas-pro \
  --namespace acas-pro \
  --set image.tag=v1.1.0
```

## 📊 Scaling

### Horizontal Pod Autoscaler

```bash
# View current replicas
kubectl get hpa -n acas-pro

# Scale manually
kubectl scale deployment acas-pro-app --replicas=5 -n acas-pro

# Autoscale based on CPU
kubectl autoscale deployment acas-pro-app \
  --min=3 --max=10 --cpu-percent=70 \
  -n acas-pro
```

### Vertical Pod Autoscaler

```bash
# Install VPA
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vpa-release-0.13.0/vpa-v1.yaml

# Apply VPA config
kubectl apply -f k8s/vpa.yaml
```

## 🔒 Security

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: acas-pro-network-policy
  namespace: acas-pro
spec:
  podSelector:
    matchLabels:
      app: acas-pro
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 5000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### Pod Security Standards

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: acas-pro-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

## 📈 Monitoring

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: acas-pro-metrics
  namespace: acas-pro
spec:
  selector:
    matchLabels:
      app: acas-pro
  endpoints:
  - port: http
    interval: 30s
    path: /metrics
```

### Grafana Dashboard

Import dashboard from `monitoring/grafana-dashboard.json`

## 🔄 CI/CD Pipeline

### GitHub Actions → Kubernetes

```yaml
# .github/workflows/deploy-k8s.yml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -t acas-pro:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker tag acas-pro:${{ github.sha }} registry.example.com/acas-pro:${{ github.sha }}
          docker push registry.example.com/acas-pro:${{ github.sha }}
      
      - name: Deploy to K8s
        run: |
          kubectl set image deployment/acas-pro-app app=registry.example.com/acas-pro:${{ github.sha }} -n acas-pro
          kubectl rollout status deployment/acas-pro-app -n acas-pro
```

## 🛠️ Troubleshooting

### Pod not starting

```bash
# Check events
kubectl get events -n acas-pro --sort-by='.lastTimestamp'

# Check logs
kubectl logs -f deployment/acas-pro-app -n acas-pro

# Describe pod
kubectl describe pod <pod-name> -n acas-pro
```

### Database connection issues

```bash
# Check database pod
kubectl get pods -n acas-pro -l app=postgres

# Check database logs
kubectl logs -f deployment/postgres -n acas-pro

# Test connection
kubectl exec -it deployment/acas-pro-app -n acas-pro -- python -c "
from acas_pro.core.database import DatabaseManager
db = DatabaseManager()
print(db.execute_one('SELECT 1'))
"
```

## 📚 Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [ACAS Pro GitHub](https://github.com/gaozhizhongke-wq/ACAS-Pro)
