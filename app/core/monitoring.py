"""
Core monitoring module with dual metrics registry system.

This module provides HTTP metrics collection using both Prometheus and OpenTelemetry
to ensure metrics appear in monitoring infrastructure regardless of collection method.
"""

import logging
import time
from typing import Dict, Any, Optional, Union, Callable

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


class EnhancedHTTPMetricsMiddleware:
    """
    FastAPI middleware for collecting standardized HTTP metrics.
    
    This middleware collects three core metrics for all HTTP requests:
    1. http_requests_total - Counter of total requests
    2. http_request_duration - Histogram of request durations
    3. http_requests_in_flight - Gauge of concurrent requests
    
    Metrics are recorded to both Prometheus and OpenTelemetry systems
    to ensure visibility regardless of collection method.
    """
    
    def __init__(self, app):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application instance
        """
        self.app = app
        logger.info("EnhancedHTTPMetricsMiddleware initialized")
    
    async def __call__(self, scope, receive, send):
        """
        ASGI middleware implementation.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            # Only process HTTP requests
            await self.app(scope, receive, send)
            return
        
        # Extract request information
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        
        # High-precision timing
        start_time = time.perf_counter()
        
        # Track in-flight requests
        in_flight_incremented = False
        
        try:
            # Increment in-flight counter
            self._increment_in_flight()
            in_flight_incremented = True
            
            # Process the request
            status_code = 500  # Default to 500 in case of unhandled exceptions
            
            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 500)
                await send(message)
            
            # Call the next middleware/application
            await self.app(scope, receive, send_wrapper)
            
        except Exception as e:
            # Log the exception but don't re-raise to avoid breaking request processing
            logger.error(f"Exception during request processing: {e}", exc_info=True)
            status_code = 500
            
            # Send error response if not already sent
            try:
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error": "Internal server error"}',
                })
            except Exception as send_error:
                logger.error(f"Failed to send error response: {send_error}")
            
        finally:
            # Always decrement in-flight counter if it was incremented
            if in_flight_incremented:
                self._decrement_in_flight()
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract route pattern and record metrics
            path_pattern = self._extract_route_pattern(path)
            self._record_metrics(method, path_pattern, str(status_code), duration_ms)
    
    def _increment_in_flight(self) -> None:
        """
        Increment the in-flight requests counter for both metrics systems.
        
        Uses comprehensive error handling to ensure request processing
        continues even if metrics recording fails. Records identical values
        to both Prometheus and OpenTelemetry systems.
        """
        prometheus_success = False
        opentelemetry_success = False
        
        # Increment Prometheus in-flight gauge
        try:
            HTTP_REQUESTS_IN_FLIGHT.inc()
            logger.debug("Prometheus in-flight counter incremented successfully")
            prometheus_success = True
        except Exception as e:
            logger.error(
                "Failed to increment Prometheus in-flight counter",
                extra={"error": str(e), "error_type": type(e).__name__, "operation": "increment"}
            )
        
        # Increment OpenTelemetry in-flight counter
        try:
            if otel_http_requests_in_flight:
                otel_http_requests_in_flight.add(1)
                logger.debug("OpenTelemetry in-flight counter incremented successfully")
                opentelemetry_success = True
            else:
                logger.debug("OpenTelemetry in-flight counter not available (using dummy metric)")
                opentelemetry_success = True  # Consider dummy metrics as "successful"
        except Exception as e:
            logger.error(
                "Failed to increment OpenTelemetry in-flight counter",
                extra={"error": str(e), "error_type": type(e).__name__, "operation": "increment"}
            )
        
        # Log overall operation status
        if not (prometheus_success or opentelemetry_success):
            logger.error("All in-flight counter increment operations failed")
    
    def _decrement_in_flight(self) -> None:
        """
        Decrement the in-flight requests counter for both metrics systems.
        
        Uses comprehensive error handling to ensure request processing
        continues even if metrics recording fails. Records identical values
        to both Prometheus and OpenTelemetry systems.
        """
        prometheus_success = False
        opentelemetry_success = False
        
        # Decrement Prometheus in-flight gauge
        try:
            HTTP_REQUESTS_IN_FLIGHT.dec()
            logger.debug("Prometheus in-flight counter decremented successfully")
            prometheus_success = True
        except Exception as e:
            logger.error(
                "Failed to decrement Prometheus in-flight counter",
                extra={"error": str(e), "error_type": type(e).__name__, "operation": "decrement"}
            )
        
        # Decrement OpenTelemetry in-flight counter
        try:
            if otel_http_requests_in_flight:
                otel_http_requests_in_flight.add(-1)
                logger.debug("OpenTelemetry in-flight counter decremented successfully")
                opentelemetry_success = True
            else:
                logger.debug("OpenTelemetry in-flight counter not available (using dummy metric)")
                opentelemetry_success = True  # Consider dummy metrics as "successful"
        except Exception as e:
            logger.error(
                "Failed to decrement OpenTelemetry in-flight counter",
                extra={"error": str(e), "error_type": type(e).__name__, "operation": "decrement"}
            )
        
        # Log overall operation status
        if not (prometheus_success or opentelemetry_success):
            logger.error("All in-flight counter decrement operations failed")
    
    def _record_metrics(self, method: str, path: str, status: str, duration_ms: float) -> None:
        """
        Record HTTP metrics to both Prometheus and OpenTelemetry systems.
        
        This method ensures identical metric values are recorded to both systems
        with independent error handling to maintain system reliability.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Route pattern (e.g., /api/v1/securities/{id})
            status: HTTP status code as string
            duration_ms: Request duration in milliseconds
        """
        # Normalize method to uppercase
        method_label = self._get_method_label(method)
        
        # Create structured logging context
        log_context = {
            "method": method_label,
            "path": path,
            "status": status,
            "duration_ms": round(duration_ms, 2)
        }
        
        # Track recording success for both systems
        prometheus_success = False
        opentelemetry_success = False
        
        # Record Prometheus metrics with individual error handling
        # Counter metric
        try:
            HTTP_REQUESTS_TOTAL.labels(
                method=method_label,
                path=path,
                status=status
            ).inc()
            logger.debug("Prometheus request counter recorded successfully", extra=log_context)
        except Exception as e:
            logger.error(
                "Failed to record Prometheus request counter",
                extra={**log_context, "error": str(e), "error_type": type(e).__name__}
            )
        
        # Histogram metric
        try:
            HTTP_REQUEST_DURATION.labels(
                method=method_label,
                path=path,
                status=status
            ).observe(duration_ms)
            logger.debug("Prometheus request duration recorded successfully", extra=log_context)
            prometheus_success = True
        except Exception as e:
            logger.error(
                "Failed to record Prometheus request duration",
                extra={**log_context, "error": str(e), "error_type": type(e).__name__}
            )
        
        # Record OpenTelemetry metrics with individual error handling
        attributes = {
            "method": method_label,
            "path": path,
            "status": status
        }
        
        # Counter metric
        try:
            if otel_http_requests_total:
                otel_http_requests_total.add(1, attributes=attributes)
                logger.debug("OpenTelemetry request counter recorded successfully", extra=log_context)
            else:
                logger.debug("OpenTelemetry request counter not available (using dummy metric)", extra=log_context)
        except Exception as e:
            logger.error(
                "Failed to record OpenTelemetry request counter",
                extra={**log_context, "error": str(e), "error_type": type(e).__name__}
            )
        
        # Histogram metric
        try:
            if otel_http_request_duration:
                otel_http_request_duration.record(duration_ms, attributes=attributes)
                logger.debug("OpenTelemetry request duration recorded successfully", extra=log_context)
                opentelemetry_success = True
            else:
                logger.debug("OpenTelemetry request duration not available (using dummy metric)", extra=log_context)
                opentelemetry_success = True  # Consider dummy metrics as "successful" to avoid false alarms
        except Exception as e:
            logger.error(
                "Failed to record OpenTelemetry request duration",
                extra={**log_context, "error": str(e), "error_type": type(e).__name__}
            )
        
        # Log overall recording status
        if prometheus_success and opentelemetry_success:
            logger.debug("Dual metrics recording completed successfully", extra=log_context)
        elif prometheus_success or opentelemetry_success:
            logger.warning(
                "Partial metrics recording success",
                extra={
                    **log_context,
                    "prometheus_success": prometheus_success,
                    "opentelemetry_success": opentelemetry_success
                }
            )
        else:
            logger.error(
                "All metrics recording failed",
                extra={
                    **log_context,
                    "prometheus_success": prometheus_success,
                    "opentelemetry_success": opentelemetry_success
                }
            )
        
        # Log slow requests with structured context
        if duration_ms > 1000:
            logger.warning(
                "Slow request detected",
                extra={**log_context, "threshold_ms": 1000}
            )
    
    def _extract_route_pattern(self, path: str) -> str:
        """
        Extract route pattern from request path to prevent high cardinality.
        
        This is a basic implementation that will be enhanced in later tasks.
        For now, it returns the path as-is but will be replaced with
        proper pattern extraction logic.
        
        Args:
            path: Original request path
            
        Returns:
            Route pattern (currently just the original path)
        """
        # TODO: This will be implemented in task 6
        # For now, return the path as-is to prevent breaking the middleware
        return path
    
    def _get_method_label(self, method: str) -> str:
        """
        Convert HTTP method to uppercase string for consistent labeling.
        
        Args:
            method: HTTP method string
            
        Returns:
            Uppercase method string
        """
        try:
            return method.upper() if method else "UNKNOWN"
        except Exception as e:
            logger.error(f"Failed to format method label: {e}")
            return "UNKNOWN"