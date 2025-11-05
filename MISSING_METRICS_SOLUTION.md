# Missing Standard Python/Flask Metrics - Solution

## Problem Summary
You were missing several standard Python runtime and HTTP client metrics that should be available in a typical Python/Flask application with OpenTelemetry.

**Expected metrics you were missing:**
- `http_client_duration_milliseconds_*`
- `process_cpu_seconds_total`
- `process_max_fds`
- `process_open_fds` 
- `process_resident_memory_bytes`
- `process_start_time_seconds`
- `process_virtual_memory_bytes`
- `python_gc_collections_total`
- `python_gc_objects_collected_total`
- `python_info`
- `python_threads`

## Root Cause
Your application was missing the OpenTelemetry system metrics instrumentation package that provides standard Python runtime and system metrics.

## Solution Implemented

### 1. Added Missing Instrumentation Packages
Updated `pyproject.toml` to include:
```toml
"opentelemetry-instrumentation-system-metrics>=0.45b0",
"opentelemetry-instrumentation-httpx>=0.45b0", 
"opentelemetry-instrumentation-requests>=0.45b0",
"opentelemetry-exporter-otlp-proto-http>=1.25.0",
"opentelemetry-instrumentation-asgi>=0.45b0",
```

### 2. Updated Application Initialization
Modified `app/main.py` to initialize the system metrics instrumentation:
```python
# Initialize additional instrumentation for standard Python metrics
if SYSTEM_METRICS_AVAILABLE:
    try:
        SystemMetricsInstrumentor().instrument()
        print("✅ System metrics instrumentation initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize system metrics: {e}")

if HTTPX_AVAILABLE:
    try:
        HTTPXClientInstrumentor().instrument()
        print("✅ HTTPX client instrumentation initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize HTTPX instrumentation: {e}")

if REQUESTS_AVAILABLE:
    try:
        RequestsInstrumentor().instrument()
        print("✅ Requests client instrumentation initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize Requests instrumentation: {e}")
```

## Metrics Now Available

### Process/Runtime Metrics (OpenTelemetry names → Prometheus names)
- `process.cpu.time` → `process_cpu_seconds_total`
- `process.memory.usage` → `process_resident_memory_bytes`
- `process.memory.virtual` → `process_virtual_memory_bytes`
- `process.open_file_descriptor.count` → `process_open_fds`
- `process.thread.count` → `python_threads`
- `process.runtime.cpython.gc_count` → `python_gc_collections_total`

### HTTP Client Metrics
- `http.client.duration` → `http_client_duration_milliseconds_*`

### System Metrics (bonus)
- `system.cpu.time`
- `system.cpu.utilization`
- `system.memory.usage`
- `system.memory.utilization`
- `system.network.io`
- `system.disk.io`

## Metric Name Transformation

The OpenTelemetry Collector should be configured to transform the OpenTelemetry semantic convention names to Prometheus-style names. This is typically done in the collector's configuration.

**Example transformation rules needed:**
```yaml
processors:
  metricstransform:
    transforms:
      - include: process.cpu.time
        match_type: strict
        action: update
        new_name: process_cpu_seconds_total
      - include: process.memory.usage
        match_type: strict  
        action: update
        new_name: process_resident_memory_bytes
      - include: process.memory.virtual
        match_type: strict
        action: update
        new_name: process_virtual_memory_bytes
      - include: process.open_file_descriptor.count
        match_type: strict
        action: update
        new_name: process_open_fds
      - include: process.thread.count
        match_type: strict
        action: update
        new_name: python_threads
      - include: process.runtime.cpython.gc_count
        match_type: strict
        action: update
        new_name: python_gc_collections_total
      - include: http.client.duration
        match_type: strict
        action: update
        new_name: http_client_duration_milliseconds
```

## Still Missing Metrics

Some metrics may still be missing and might need additional configuration:
- `process_max_fds` - May need system-level configuration
- `process_start_time_seconds` - May need additional instrumentation
- `python_gc_objects_collected_total` - May be available as a different metric name
- `python_info` - May need additional Python info instrumentation

## Next Steps

### 1. Deploy the Updated Application
```bash
# Install new dependencies
uv sync

# Build and deploy
./kbuild.sh
kubectl apply -f k8s/deployment.yaml
```

### 2. Verify Metrics
```bash
# Check that new metrics are being generated
./troubleshoot-otel.sh

# Look for the new process and system metrics
kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/metrics | grep -E "process_|system_|http_client"
```

### 3. Configure OpenTelemetry Collector
Ensure your OpenTelemetry Collector is configured to:
1. Receive the new metrics from your application
2. Transform metric names from OpenTelemetry format to Prometheus format
3. Export to Prometheus with the expected naming convention

### 4. Verify in Prometheus
After deployment, check Prometheus for the transformed metrics:
- `process_cpu_seconds_total{service_name="globeco-security-service"}`
- `process_resident_memory_bytes{service_name="globeco-security-service"}`
- `http_client_duration_milliseconds{service_name="globeco-security-service"}`

## Testing Locally
You can test the new metrics locally:
```bash
python test-standard-metrics.py
```

This will show you all the metrics being generated by the system metrics instrumentation.