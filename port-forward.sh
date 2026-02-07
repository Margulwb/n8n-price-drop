#!/bin/bash

echo "Starting port-forward manager..."

until kubectl get nodes &> /dev/null; do
  echo "Waiting for Kubernetes API to be reachable..."
  sleep 5
done

echo "Kubernetes API is up! Starting port-forward..."
echo "Access at: http://localhost:8080"

while true; do
  kubectl port-forward svc/price-drop-svc 8080:80
  echo "Port-forward crashed or stopped. Restarting in 5s..."
  sleep 5
done