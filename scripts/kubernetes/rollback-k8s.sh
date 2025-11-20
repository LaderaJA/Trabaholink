#!/bin/bash
# Rollback Kubernetes deployment

set -e

echo "↩️  Kubernetes Rollback Script"
echo "============================="
echo ""

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed!"
    exit 1
fi

# Select namespace
echo "📝 Select environment to rollback:"
echo "1) Development (trabaholink-dev)"
echo "2) Staging (trabaholink-staging)"
echo "3) Production (trabaholink-prod)"
read -p "Enter choice (1-3): " ENV_CHOICE

case $ENV_CHOICE in
    1) NAMESPACE="trabaholink-dev" ;;
    2) NAMESPACE="trabaholink-staging" ;;
    3) NAMESPACE="trabaholink-prod" ;;
    *)
        echo "❌ Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "🔍 Rollout history for namespace: $NAMESPACE"
echo ""

# Show rollout history
kubectl rollout history deployment/trabaholink-web -n "$NAMESPACE"

echo ""
read -p "Enter revision number to rollback to (or 'latest' for previous): " REVISION

if [ "$REVISION" = "latest" ]; then
    echo ""
    echo "↩️  Rolling back to previous revision..."
    kubectl rollout undo deployment/trabaholink-web -n "$NAMESPACE"
else
    echo ""
    echo "↩️  Rolling back to revision $REVISION..."
    kubectl rollout undo deployment/trabaholink-web -n "$NAMESPACE" --to-revision="$REVISION"
fi

# Wait for rollback
echo ""
echo "⏳ Waiting for rollback to complete..."
kubectl rollout status deployment/trabaholink-web -n "$NAMESPACE"

echo ""
echo "✅ Rollback complete!"
echo ""
kubectl get pods -n "$NAMESPACE" -l app=trabaholink
