#!/bin/bash

echo "🔍 OpenTelemetry Troubleshooting Script"
echo "======================================"

# Check if OpenTelemetry Collector exists
echo "1. Checking for OpenTelemetry Collector services..."
OTEL_SERVICES=$(kubectl get svc -A | grep otel)
if [ -z "$OTEL_SERVICES" ]; then
    echo "❌ No OpenTelemetry Collector services found!"
    echo "   Please ensure the OTEL Collector is deployed."
else
    echo "✅ Found OpenTelemetry services:"
    echo "$OTEL_SERVICES"
fi

echo ""

# Check specific namespaces
echo "2. Checking common namespaces for OTEL Collector..."
for ns in default monitoring observability kube-system; do
    COLLECTOR=$(kubectl get svc -n $ns 2>/dev/null | grep otel-collector || echo "")
    if [ ! -z "$COLLECTOR" ]; then
        echo "✅ Found in namespace '$ns':"
        echo "   $COLLECTOR"
    fi
done

echo ""

# Check our service pod
echo "3. Checking GlobeCo Security Service pod..."
POD_NAME=$(kubectl get pods -n globeco -l app=globeco-security-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "❌ GlobeCo Security Service pod not found!"
    exit 1
fi

echo "✅ Pod: $POD_NAME"

# Check environment variables
echo ""
echo "4. Environment variables in pod:"
kubectl exec -n globeco $POD_NAME -- env | grep -E "OTEL|ENABLE_METRICS" | sort

echo ""

# Test DNS resolution
echo "5. Testing DNS resolution from pod..."
for endpoint in \
    "otel-collector-collector.monitoring.svc.cluster.local" \
    "otel-collector-collector.default.svc.cluster.local" \
    "otel-collector.monitoring.svc.cluster.local" \
    "otel-collector.default.svc.cluster.local"; do
    
    echo -n "   Testing $endpoint: "
    if kubectl exec -n globeco $POD_NAME -- nslookup $endpoint >/dev/null 2>&1; then
        echo "✅ Resolved"
    else
        echo "❌ Failed"
    fi
done

echo ""

# Check application logs for OTEL-related messages
echo "6. Recent OTEL-related logs:"
kubectl logs -n globeco $POD_NAME --tail=100 | grep -i -E "otel|opentelemetry|metric|trace|exporter" | tail -10

echo ""

# Test metrics endpoint
echo "7. Testing /metrics endpoint availability:"
METRICS_TEST=$(kubectl exec -n globeco $POD_NAME -- curl -s -w "%{http_code}" -o /dev/null http://localhost:8000/metrics 2>/dev/null)
if [ "$METRICS_TEST" = "200" ]; then
    echo "✅ /metrics endpoint responding (HTTP 200)"
    echo "   Sample metrics:"
    kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/metrics | grep -E "http_requests_total|http_request_duration" | head -5
else
    echo "❌ /metrics endpoint not responding (HTTP $METRICS_TEST)"
fi

echo ""

# Check for common OTEL Collector configurations
echo "8. Suggested fixes:"
echo "   - Ensure OTEL Collector is deployed and running"
echo "   - Verify the correct namespace in OTEL_EXPORTER_OTLP_ENDPOINT"
echo "   - Check if OTEL Collector is configured to receive OTLP on port 4317/4318"
echo "   - Verify network policies allow communication between namespaces"
echo "   - Check OTEL Collector logs for connection errors"

echo ""
echo "🔧 To manually test OTEL connectivity:"
echo "   kubectl exec -n globeco $POD_NAME -- telnet otel-collector-collector.monitoring.svc.cluster.local 4317"

echo ""
echo "9. Testing custom HTTP metrics specifically:"
echo "   Looking for http_requests_total, http_request_duration, http_requests_in_flight..."
CUSTOM_METRICS=$(kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/metrics | grep -E "^http_requests_total|^http_request_duration|^http_requests_in_flight" | wc -l)
if [ "$CUSTOM_METRICS" -gt 0 ]; then
    echo "✅ Custom HTTP metrics found in /metrics endpoint ($CUSTOM_METRICS metrics)"
    echo "   Sample custom metrics:"
    kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/metrics | grep -E "^http_requests_total|^http_request_duration|^http_requests_in_flight" | head -3
else
    echo "❌ Custom HTTP metrics NOT found in /metrics endpoint"
fi

echo ""
echo "10. Checking for OpenTelemetry initialization logs:"
kubectl logs -n globeco $POD_NAME --tail=200 | grep -i -E "opentelemetry.*metric.*initialized|otel.*metric.*created|meter.*provider" | tail -5