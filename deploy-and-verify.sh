#!/bin/bash

echo "🚀 Deploying GlobeCo Security Service with OpenTelemetry configuration..."

# Apply the deployment
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/globeco-security-service -n globeco --timeout=300s

echo "📊 Checking OpenTelemetry Collector connectivity..."

# Get the pod name
POD_NAME=$(kubectl get pods -n globeco -l app=globeco-security-service -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "❌ No pods found for globeco-security-service"
    exit 1
fi

echo "🔍 Pod: $POD_NAME"

# Check environment variables
echo "🔧 Environment variables:"
kubectl exec -n globeco $POD_NAME -- env | grep OTEL

# Test connectivity to OTEL collector
echo "🌐 Testing connectivity to OpenTelemetry Collector..."
kubectl exec -n globeco $POD_NAME -- nslookup otel-collector-collector.monitoring.svc.cluster.local || \
kubectl exec -n globeco $POD_NAME -- nslookup otel-collector-collector.default.svc.cluster.local

# Check if the collector service exists
echo "🔍 Checking for OpenTelemetry Collector services..."
kubectl get svc -A | grep otel-collector

# Check application logs for OTEL errors
echo "📋 Recent application logs (looking for OTEL issues):"
kubectl logs -n globeco $POD_NAME --tail=50 | grep -i "otel\|opentelemetry\|metric\|trace" || echo "No OTEL-related logs found"

# Test the /metrics endpoint
echo "🎯 Testing /metrics endpoint..."
kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/metrics | head -20

echo "✅ Deployment verification complete!"
echo ""
echo "Next steps:"
echo "1. Check Prometheus targets to see if metrics are being scraped"
echo "2. Verify OpenTelemetry Collector is receiving metrics"
echo "3. Check Jaeger for traces if tracing is enabled"