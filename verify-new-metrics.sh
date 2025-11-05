#!/bin/bash

echo "🔍 Verifying New Standard Python Metrics"
echo "========================================"

# Get pod name
POD_NAME=$(kubectl get pods -n globeco -l app=globeco-security-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "❌ GlobeCo Security Service pod not found!"
    echo "   Make sure the service is deployed to the 'globeco' namespace"
    exit 1
fi

echo "✅ Pod: $POD_NAME"
echo ""

# Check if the new instrumentation is initialized
echo "1. Checking initialization logs..."
kubectl logs -n globeco $POD_NAME --tail=50 | grep -E "System metrics|HTTPX|Requests.*instrumentation initialized" | head -5

echo ""

# Check for new metrics in /metrics endpoint
echo "2. Checking for new process metrics..."
PROCESS_METRICS=$(kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/metrics | grep -E "^process_|^system_|^http_client" | wc -l)

if [ "$PROCESS_METRICS" -gt 0 ]; then
    echo "✅ Found $PROCESS_METRICS new process/system metrics in /metrics endpoint"
    echo "   Sample metrics:"
    kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/metrics | grep -E "^process_|^system_|^http_client" | head -5
else
    echo "❌ No new process/system metrics found in /metrics endpoint"
    echo "   This might be expected if metrics are only exported via OpenTelemetry"
fi

echo ""

# Check application logs for metric export
echo "3. Checking OpenTelemetry metric export..."
OTEL_LOGS=$(kubectl logs -n globeco $POD_NAME --tail=100 | grep -i -E "metric.*export|system.*metric" | wc -l)

if [ "$OTEL_LOGS" -gt 0 ]; then
    echo "✅ Found OpenTelemetry metrics activity in logs"
    kubectl logs -n globeco $POD_NAME --tail=100 | grep -i -E "metric.*export|system.*metric" | tail -3
else
    echo "⚠️ No obvious OpenTelemetry metrics activity in recent logs"
fi

echo ""

# Generate some activity to trigger metrics
echo "4. Generating activity to trigger metrics..."
kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/health >/dev/null
kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/api/v1/securities >/dev/null
echo "✅ Made test requests to generate metrics"

echo ""

# Expected metrics summary
echo "5. Expected metrics that should now be available:"
echo "   📊 Process Metrics:"
echo "      - process_cpu_seconds_total (from process.cpu.time)"
echo "      - process_resident_memory_bytes (from process.memory.usage)"
echo "      - process_virtual_memory_bytes (from process.memory.virtual)"
echo "      - process_open_fds (from process.open_file_descriptor.count)"
echo "      - python_threads (from process.thread.count)"
echo "      - python_gc_collections_total (from process.runtime.cpython.gc_count)"
echo ""
echo "   🌐 HTTP Client Metrics:"
echo "      - http_client_duration_milliseconds_* (from http.client.duration)"
echo ""
echo "   🖥️ System Metrics (bonus):"
echo "      - system_cpu_time, system_memory_usage, system_network_io, etc."

echo ""
echo "6. Next steps:"
echo "   - Check your OpenTelemetry Collector logs for received metrics"
echo "   - Verify Prometheus is scraping the transformed metrics"
echo "   - Look for metrics with service_name='globeco-security-service'"

echo ""
echo "✅ Verification completed!"