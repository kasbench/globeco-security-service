# OpenTelemetry Custom Metrics Fix Summary

## The Problem
Your custom HTTP metrics (`http_requests_total`, `http_request_duration`, `http_requests_in_flight`) were appearing in the `/metrics` endpoint but not flowing to Prometheus via the OpenTelemetry Collector.

## Root Cause
The issue was that your `monitoring.py` module was creating its **own** OpenTelemetry meter provider, which was separate from the one configured in `main.py` that connects to your OTEL Collector. This meant:

1. **Prometheus metrics** (visible at `/metrics`) were using the `prometheus_client` library
2. **OpenTelemetry metrics** were using a separate, disconnected meter provider
3. Only the Prometheus metrics were being recorded, not the OTEL metrics

## What I Fixed

### 1. Fixed OpenTelemetry Meter Provider Usage (`app/core/monitoring.py`)
- Removed the separate meter provider creation in `monitoring.py`
- Changed to use the **global** meter provider set up in `main.py`
- Added `setup_otel_metrics()` function to initialize OTEL metrics after the global provider is ready

### 2. Updated Initialization Order (`app/main.py`)
- Added call to `setup_monitoring(app)` right after the meter provider is initialized
- This ensures OTEL metrics are created using the correct, connected meter provider

### 3. Environment Variables (`k8s/deployment.yaml`)
- Already configured correctly with OTEL Collector endpoint

## Files Changed
- `app/core/monitoring.py` - Fixed OTEL meter provider usage
- `app/main.py` - Updated initialization order
- `troubleshoot-otel.sh` - Added custom metrics checks
- `test-otel-metrics.py` - Created test script

## Next Steps

### 1. Deploy the Fix
```bash
# Build and deploy the updated service
./kbuild.sh
kubectl apply -f k8s/deployment.yaml

# Wait for rollout
kubectl rollout status deployment/globeco-security-service -n globeco
```

### 2. Verify the Fix
```bash
# Run the troubleshooting script
./troubleshoot-otel.sh

# Or run the deployment verification script
./deploy-and-verify.sh
```

### 3. Test Locally (Optional)
```bash
# Test OTEL metrics setup locally
python test-otel-metrics.py
```

### 4. Generate Some Traffic
```bash
# Make some requests to generate metrics
POD_NAME=$(kubectl get pods -n globeco -l app=globeco-security-service -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/health
kubectl exec -n globeco $POD_NAME -- curl -s http://localhost:8000/api/v1/securities
```

### 5. Check Prometheus
After generating traffic, check Prometheus for these metrics:
- `http_requests_total{service_name="globeco-security-service"}`
- `http_request_duration{service_name="globeco-security-service"}`
- `http_requests_in_flight{service_name="globeco-security-service"}`

## Expected Behavior After Fix

1. **Custom HTTP metrics** should appear in both:
   - `/metrics` endpoint (Prometheus format)
   - OpenTelemetry Collector (OTLP format)

2. **Prometheus** should receive the custom metrics via the OTEL Collector

3. **Logs** should show successful OTEL metrics initialization

## Troubleshooting

If metrics still don't appear in Prometheus:

1. **Check OTEL Collector logs** for received metrics
2. **Verify Prometheus configuration** to scrape from OTEL Collector
3. **Check network connectivity** between services
4. **Verify OTEL Collector configuration** for metric forwarding to Prometheus

## Key Technical Details

- **Dual Metrics System**: The service now properly records to both Prometheus (for `/metrics`) and OpenTelemetry (for Collector)
- **Shared Meter Provider**: Both systems use the same OTEL meter provider configured in `main.py`
- **Proper Initialization Order**: OTEL metrics are created after the meter provider is set up
- **Error Handling**: Fallback to dummy metrics if OTEL setup fails