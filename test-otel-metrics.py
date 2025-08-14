#!/usr/bin/env python3
"""
Test script to verify OpenTelemetry metrics are being created and exported correctly.
"""

import asyncio
import sys
import os
import time
import logging

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings
from app.core.monitoring import setup_otel_metrics, get_metrics_registry_info

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_otel_metrics():
    """Test OpenTelemetry metrics setup and functionality."""
    
    print("🔍 Testing OpenTelemetry Metrics Setup")
    print("=" * 50)
    
    # Print current configuration
    print(f"OTEL_EXPORTER_OTLP_ENDPOINT: {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
    print(f"OTEL_SERVICE_NAME: {settings.OTEL_SERVICE_NAME}")
    print(f"OTEL_EXPORTER_OTLP_INSECURE: {settings.OTEL_EXPORTER_OTLP_INSECURE}")
    print(f"ENABLE_METRICS: {settings.enable_metrics}")
    print()
    
    # Setup OpenTelemetry like in main.py
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPMetricExporterGRPC
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPMetricExporterHTTP
    from opentelemetry.sdk.resources import Resource
    
    # Create resource
    resource = Resource.create({
        "service.name": settings.OTEL_SERVICE_NAME
    })
    
    # Create metric readers
    metric_readers = [
        PeriodicExportingMetricReader(
            OTLPMetricExporterGRPC(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=settings.OTEL_EXPORTER_OTLP_INSECURE
            ),
            export_interval_millis=5000
        ),
        PeriodicExportingMetricReader(
            OTLPMetricExporterHTTP(
                endpoint=f"http://otel-collector-collector.monitoring.svc.cluster.local:4318/v1/metrics"
            ),
            export_interval_millis=5000
        )
    ]
    
    # Create and set meter provider
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    otel_metrics.set_meter_provider(meter_provider)
    
    print("✅ OpenTelemetry meter provider initialized")
    
    # Setup OTEL metrics
    setup_otel_metrics()
    print("✅ OTEL metrics setup completed")
    
    # Get registry info
    registry_info = get_metrics_registry_info()
    print(f"📊 Metrics registry info: {registry_info}")
    
    # Test the metrics by importing and using them
    from app.core.monitoring import (
        otel_http_requests_total,
        otel_http_request_duration,
        otel_http_requests_in_flight
    )
    
    print("\n🧪 Testing metric recording...")
    
    # Test counter
    try:
        otel_http_requests_total.add(1, attributes={
            "method": "GET",
            "path": "/test",
            "status": "200"
        })
        print("✅ Counter metric recorded successfully")
    except Exception as e:
        print(f"❌ Counter metric failed: {e}")
    
    # Test histogram
    try:
        otel_http_request_duration.record(123.45, attributes={
            "method": "GET",
            "path": "/test",
            "status": "200"
        })
        print("✅ Histogram metric recorded successfully")
    except Exception as e:
        print(f"❌ Histogram metric failed: {e}")
    
    # Test up-down counter
    try:
        otel_http_requests_in_flight.add(1)
        otel_http_requests_in_flight.add(-1)
        print("✅ Up-down counter metric recorded successfully")
    except Exception as e:
        print(f"❌ Up-down counter metric failed: {e}")
    
    print("\n⏳ Waiting 6 seconds for metrics to be exported...")
    await asyncio.sleep(6)
    
    print("✅ Test completed!")
    print("\nNext steps:")
    print("1. Check OpenTelemetry Collector logs for received metrics")
    print("2. Check Prometheus for the new metrics")
    print("3. If metrics still don't appear, check collector configuration")

if __name__ == "__main__":
    asyncio.run(test_otel_metrics())