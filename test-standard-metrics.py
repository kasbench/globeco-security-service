#!/usr/bin/env python3
"""
Test script to verify standard OpenTelemetry metrics are being generated.
This script will help identify which metrics should be available.
"""

import time
import httpx
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource

# Initialize OpenTelemetry with console exporter for testing
resource = Resource.create({"service.name": "test-metrics"})
console_reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter(),
    export_interval_millis=3000
)
meter_provider = MeterProvider(resource=resource, metric_readers=[console_reader])
metrics.set_meter_provider(meter_provider)

# Initialize instrumentations
try:
    from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
    SystemMetricsInstrumentor().instrument()
    print("✅ System metrics instrumentation initialized")
except ImportError as e:
    print(f"❌ System metrics not available: {e}")

try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HTTPXClientInstrumentor().instrument()
    print("✅ HTTPX client instrumentation initialized")
except ImportError as e:
    print(f"❌ HTTPX instrumentation not available: {e}")

try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    RequestsInstrumentor().instrument()
    print("✅ Requests client instrumentation initialized")
except ImportError as e:
    print(f"❌ Requests instrumentation not available: {e}")

print("\n🔍 Expected standard metrics that should be generated:")
print("System/Process metrics from system_metrics instrumentation:")
print("- process.cpu.time")
print("- process.memory.usage") 
print("- process.memory.virtual")
print("- process.open_file_descriptor.count")
print("- process.thread.count")
print("- process.runtime.memory")
print("- process.runtime.cpu.time")
print("- process.runtime.gc_count")
print("- cpython.gc.collections")
print("- cpython.gc.collected_objects")
print("- process.runtime.thread_count")

print("\nHTTP Client metrics from httpx/requests instrumentation:")
print("- http.client.duration")
print("- http.client.request.size")
print("- http.client.response.size")

print("\n⏳ Generating some activity and waiting for metrics...")

# Generate some HTTP activity to trigger client metrics
try:
    async def make_requests():
        async with httpx.AsyncClient() as client:
            await client.get("https://httpbin.org/get")
            await client.post("https://httpbin.org/post", json={"test": "data"})
    
    import asyncio
    asyncio.run(make_requests())
    print("✅ Made HTTP requests to generate client metrics")
except Exception as e:
    print(f"⚠️ Failed to make HTTP requests: {e}")

# Wait for metrics to be collected and exported
time.sleep(5)

print("\n✅ Test completed. Check console output above for exported metrics.")
print("Note: Metrics are exported every 3 seconds, so you should see multiple exports.")