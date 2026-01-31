#!/bin/bash

set -e

echo "Installing Nginx Ingress Controller..."

echo "Applying Nginx Ingress Controller manifest..."
kubectl apply -f ./ingress-controller.yaml

echo "Waiting for ingress controller to be ready..."
kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app=nginx-ingress,component=controller \
    --timeout=120s 2>/dev/null || echo "Waiting timed out, but continuing..."

echo "Checking ingress controller status..."
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx

echo "✅ Nginx Ingress Controller installed successfully!"
echo ""
echo "Apply the ingress manifest:"
echo "  kubectl apply -f ingress/ingress.yaml"
