#!/bin/bash
# deploy.sh - Deploy GlobeCo Security Service to Kubernetes
# Author: Noah Krieger
# Usage: bash deploy.sh
#
# This script applies the service and deployment manifests in the correct order.
# Make executable: chmod +x deploy.sh

set -e

echo "Applying service..."
kubectl apply -f service.yaml

echo "Applying deployment..."
kubectl apply -f deployment.yaml

echo "Deployment complete." 