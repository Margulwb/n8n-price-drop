#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DOCKER_REGISTRY="margulewicz"
APP_NAME="price-drop"
NAMESPACE="default"
DEPLOYMENT_NAME="price-drop-app"
MANIFEST_PATH="$SCRIPT_DIR/price-drop/kubernetes/deployment.yaml"

echo "=========================================="
echo "Running tests..."
echo "=========================================="
cd "$SCRIPT_DIR/price-drop"
TELEGRAM_CHAT_ID=test TELEGRAM_TOKEN=test python -m pytest tests/ -v --tb=short
echo ""
echo "All tests passed!"
echo ""

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
IMAGE_TAG="${DOCKER_REGISTRY}/${APP_NAME}:${TIMESTAMP}"

echo "Image Tag: $IMAGE_TAG"
echo ""

echo "Building Docker image..."
docker build -t "$IMAGE_TAG" .
cd "$SCRIPT_DIR"

echo ""
echo "Pushing Docker image to registry..."
docker push "$IMAGE_TAG"

echo ""
echo "Updating Kubernetes manifest..."
sed -i "s|image: ${DOCKER_REGISTRY}/${APP_NAME}:[^ ]*|image: ${IMAGE_TAG}|g" "$MANIFEST_PATH"

echo "Applying manifest..."
kubectl apply -f "$MANIFEST_PATH"

echo ""
echo "Restarting deployment..."
kubectl rollout restart deployment/$DEPLOYMENT_NAME -n $NAMESPACE

echo ""
echo "Waiting for rollout to complete..."
kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE

echo ""
echo "=========================================="
echo "✅ Deployment completed successfully!"
echo "Image: $IMAGE_TAG"
echo "=========================================="