"""
Core monitoring module with dual metrics registry system.

This module provides HTTP metrics collection using both Prometheus and OpenTelemetry
to ensure metrics appear in monitoring infrastructure regardless of collection method.
"""

import logging
import time
from typing import Dict, Any, Optional, Union

# Prometheus imports
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY

# OpenTelemetry imports
try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global metrics registry to prevent duplicate registration
_METRICS_REGISTRY: Dict[str, Any] = {}

# Dummy metric classes for fallback when metrics systems fail
class DummyMetric:
    """Dummy metric that does nothing but prevents errors."""
    
    def inc(self, amount: float = 1) -> None:
        pass
    
    def dec(self, amount: float = 1) -> None:
        pass
    
    def observe(self, amount: float) -> None:
        pass
    
    def labels(self, **kwargs) -> 'DummyMetric':
        return self
    
    def set(self, value: float) -> None:
        pass


class DummyOTelMetric:
    """Dummy OpenTelemetry metric that does nothing but prevents errors."""
    
    def add(self, amount: Union[int, float], attributes: Optional[Dict[str, str]] = None) -> None:
        pass
    
    def record(self, amount: Union[int, float], attributes: Optional[Dict[str, str]] = None) -> None:
        pass


def _get_or_create_metric(metric_class, name: str, description: str, **kwargs) -> Any:
    """
    Get or create a metric, preventing duplicate registration errors.
    
    Args:
        metric_class: The Prometheus metric class (Counter, Histogram, Gauge)
        name: Metric name
        description: Metric description
        **kwargs: Additional arguments for metric creation
        
    Returns:
        The metric instance or a dummy metric if creation fails
    """
    registry_key = f"{metric_class.__name__}_{name}"
    
    if registry_key in _METRICS_REGISTRY:
        logger.debug(f"Returning existing metric: {registry_key}")
        return _METRICS_REGISTRY[registry_key]
    
    try:
        # Create the metric with provided arguments
        metric = metric_class(name, description, **kwargs)
        _METRICS_REGISTRY[registry_key] = metric
        logger.debug(f"Created new metric: {registry_key}")
        return metric
        
    except ValueError as e:
        if "Duplicated timeseries" in str(e) or "already registered" in str(e):
            logger.warning(f"Metric {name} already registered, returning dummy metric: {e}")
            dummy_metric = DummyMetric()
            _METRICS_REGISTRY[registry_key] = dummy_metric
            return dummy_metric
        else:
            logger.error(f"Failed to create metric {name}: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error creating metric {name}: {e}")
        dummy_metric = DummyMetric()
        _METRICS_REGISTRY[registry_key] = dummy_metric
        return dummy_metric


# Initialize OpenTelemetry meter if available
otel_meter = None
if OTEL_AVAILABLE:
    try:
        # Create resource with service information
        resource = Resource.create({
            "service.name": "security-service",
            "service.version": "1.0.0"
        })
        
        # Create OTLP exporter (will be configured via environment variables)
        otlp_exporter = OTLPMetricExporter()
        
        # Create meter provider with periodic export
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=5000)]
        )
        
        # Set the global meter provider
        otel_metrics.set_meter_provider(meter_provider)
        
        # Get meter for this module
        otel_meter = otel_metrics.get_meter(__name__)
        logger.info("OpenTelemetry metrics initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry metrics: {e}")
        otel_meter = None
else:
    logger.warning("OpenTelemetry not available, metrics will only be exported via Prometheus")


# Prometheus HTTP Metrics
# These will be created when the module is imported to ensure they're available
HTTP_REQUESTS_TOTAL = _get_or_create_metric(
    Counter,
    'http_requests_total',
    'Total number of HTTP requests',
    labelnames=['method', 'path', 'status']
)

HTTP_REQUEST_DURATION = _get_or_create_metric(
    Histogram,
    'http_request_duration',
    'HTTP request duration in milliseconds',
    labelnames=['method', 'path', 'status'],
    buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
)

HTTP_REQUESTS_IN_FLIGHT = _get_or_create_metric(
    Gauge,
    'http_requests_in_flight',
    'Number of HTTP requests currently being processed'
)

# OpenTelemetry HTTP Metrics
otel_http_requests_total = None
otel_http_request_duration = None
otel_http_requests_in_flight = None

if otel_meter:
    try:
        otel_http_requests_total = otel_meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="1"
        )
        
        otel_http_request_duration = otel_meter.create_histogram(
            name="http_request_duration",
            description="HTTP request duration in milliseconds",
            unit="ms"
        )
        
        otel_http_requests_in_flight = otel_meter.create_up_down_counter(
            name="http_requests_in_flight",
            description="Number of HTTP requests currently being processed",
            unit="1"
        )
        
        logger.info("OpenTelemetry HTTP metrics created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create OpenTelemetry HTTP metrics: {e}")
        # Create dummy metrics as fallback
        otel_http_requests_total = DummyOTelMetric()
        otel_http_request_duration = DummyOTelMetric()
        otel_http_requests_in_flight = DummyOTelMetric()
else:
    # Create dummy metrics if OpenTelemetry is not available
    otel_http_requests_total = DummyOTelMetric()
    otel_http_request_duration = DummyOTelMetric()
    otel_http_requests_in_flight = DummyOTelMetric()


def get_metrics_registry_info() -> Dict[str, Any]:
    """
    Get information about the current metrics registry for debugging.
    
    Returns:
        Dictionary containing registry information
    """
    return {
        "registered_metrics": list(_METRICS_REGISTRY.keys()),
        "opentelemetry_available": OTEL_AVAILABLE,
        "opentelemetry_meter_initialized": otel_meter is not None,
        "prometheus_metrics_count": len([k for k in _METRICS_REGISTRY.keys() if not k.startswith("Dummy")])
    }


def reset_metrics_registry() -> None:
    """
    Reset the metrics registry. Primarily used for testing.
    
    Warning: This should only be used in test environments.
    """
    global _METRICS_REGISTRY
    _METRICS_REGISTRY.clear()
    logger.warning("Metrics registry has been reset")