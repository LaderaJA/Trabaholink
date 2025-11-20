#!/bin/bash
# Deploy Trabaholink to Kubernetes cluster

set -e

echo "☸️  Kubernetes Deployment Script"
echo "================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../.."

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed!"
    echo "   Install: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check cluster connection
echo "🔍 Checking Kubernetes cluster connection..."
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster!"
    echo "   Make sure kubectl is configured correctly."
    exit 1
fi

CLUSTER_NAME=$(kubectl config current-context)
echo "✅ Connected to cluster: $CLUSTER_NAME"
echo ""

# Prompt for environment
echo "📝 Select deployment environment:"
echo "1) Development"
echo "2) Staging"
echo "3) Production"
read -p "Enter choice (1-3): " ENV_CHOICE

case $ENV_CHOICE in
    1)
        ENVIRONMENT="development"
        NAMESPACE="trabaholink-dev"
        ;;
    2)
        ENVIRONMENT="staging"
        NAMESPACE="trabaholink-staging"
        ;;
    3)
        ENVIRONMENT="production"
        NAMESPACE="trabaholink-prod"
        ;;
    *)
        echo "❌ Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "🎯 Deploying to: $ENVIRONMENT"
echo "📦 Namespace: $NAMESPACE"
echo ""
read -p "Continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Aborted."
    exit 0
fi

# Create namespace if it doesn't exist
echo ""
echo "📦 Creating namespace..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests
echo ""
echo "🚀 Applying Kubernetes manifests..."
cd "$PROJECT_DIR/kubernetes/base"

if command -v kustomize &> /dev/null; then
    echo "Using kustomize..."
    kustomize build . | kubectl apply -n "$NAMESPACE" -f -
else
    echo "Applying manifests directly..."
    kubectl apply -n "$NAMESPACE" -f deployment.yaml
    kubectl apply -n "$NAMESPACE" -f service.yaml
    kubectl apply -n "$NAMESPACE" -f ingress.yaml
    kubectl apply -n "$NAMESPACE" -f pvc.yaml
fi

# Wait for rollout
echo ""
echo "⏳ Waiting for deployment to complete..."
kubectl rollout status deployment/trabaholink-web -n "$NAMESPACE" --timeout=5m

# Check pod status
echo ""
echo "📊 Pod Status:"
kubectl get pods -n "$NAMESPACE" -l app=trabaholink

# Get service info
echo ""
echo "🌐 Service Information:"
kubectl get svc -n "$NAMESPACE" -l app=trabaholink

# Get ingress info
echo ""
echo "🔗 Ingress Information:"
kubectl get ingress -n "$NAMESPACE"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Useful commands:"
echo "   View pods:       kubectl get pods -n $NAMESPACE"
echo "   View logs:       kubectl logs -f -n $NAMESPACE -l app=trabaholink"
echo "   Shell access:    kubectl exec -it -n $NAMESPACE <pod-name> -- /bin/bash"
echo "   Port forward:    kubectl port-forward -n $NAMESPACE svc/trabaholink-web 8000:8000"
echo "   Delete:          kubectl delete namespace $NAMESPACE"
