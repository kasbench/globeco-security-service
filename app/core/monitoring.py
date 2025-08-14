"""
Core monitoring module with dual metrics registry system.

This module provides HTTP metrics collection using both Prometheus and OpenTelemetry
to ensure metrics appear in monitoring infrastructure regardless of collection method.
"""

import logging
import re
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
            self._record_metrics(method, path_pattern, status_code, duration_ms)
    
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
            status: HTTP status code as string or integer
            duration_ms: Request duration in milliseconds
        """
        # Normalize labels using formatting utilities
        method_label = self._get_method_label(method)
        status_label = self._format_status_code(status)
        
        # Create structured logging context
        log_context = {
            "method": method_label,
            "path": path,
            "status": status_label,
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
                status=status_label
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
                status=status_label
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
            "status": status_label
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
        
        Converts actual URLs to parameterized route patterns specific to the
        security service API structure. This prevents metric cardinality explosion
        by replacing dynamic path segments (like IDs) with parameter placeholders.
        
        Args:
            path: Original request path
            
        Returns:
            Route pattern with parameterized dynamic segments
        """
        try:
            # Handle empty or root paths
            if not path or path == "/":
                return "/"
            
            # Remove trailing slash for consistent processing
            normalized_path = path.rstrip("/")
            if not normalized_path:
                return "/"
            
            # Security service specific routing patterns
            if normalized_path.startswith("/api/v1/securities"):
                return self._extract_securities_v1_pattern(normalized_path)
            elif normalized_path.startswith("/api/v2/securities"):
                return self._extract_securities_v2_pattern(normalized_path)
            elif normalized_path.startswith("/health"):
                return self._extract_health_pattern(normalized_path)
            elif normalized_path == "/metrics":
                return "/metrics"
            elif normalized_path.startswith("/docs") or normalized_path.startswith("/openapi"):
                # FastAPI documentation endpoints
                return normalized_path
            else:
                # Handle unmatched routes with sanitization
                return self._sanitize_unmatched_route(normalized_path)
                
        except Exception as e:
            logger.error(
                "Failed to extract route pattern",
                extra={"path": path, "error": str(e), "error_type": type(e).__name__}
            )
            # Return sanitized version as fallback
            return self._sanitize_unmatched_route(path)
    
    def _extract_securities_v1_pattern(self, path: str) -> str:
        """
        Extract route patterns for /api/v1/securities endpoints.
        
        Handles the v1 securities API patterns:
        - /api/v1/securities -> /api/v1/securities
        - /api/v1/securities/{id} -> /api/v1/securities/{id}
        - /api/v1/securities/search -> /api/v1/securities/search
        
        Args:
            path: Normalized path starting with /api/v1/securities
            
        Returns:
            Route pattern for v1 securities endpoints
        """
        try:
            parts = path.split("/")
            
            # /api/v1/securities (base endpoint)
            if len(parts) == 4:  # ['', 'api', 'v1', 'securities']
                return "/api/v1/securities"
            
            # /api/v1/securities/something
            elif len(parts) == 5:
                segment = parts[4]
                
                # Known static endpoints
                if segment in ["search", "types", "categories"]:
                    return f"/api/v1/securities/{segment}"
                
                # Dynamic ID endpoint
                elif self._looks_like_id(segment):
                    return "/api/v1/securities/{id}"
                
                # Unknown segment - treat as ID for safety
                else:
                    return "/api/v1/securities/{id}"
            
            # /api/v1/securities/{id}/something (nested resources)
            elif len(parts) == 6:
                id_segment = parts[4]
                resource_segment = parts[5]
                
                # Verify the middle segment looks like an ID
                if self._looks_like_id(id_segment):
                    # Known nested resources
                    if resource_segment in ["details", "history", "transactions"]:
                        return f"/api/v1/securities/{{id}}/{resource_segment}"
                    else:
                        return f"/api/v1/securities/{{id}}/{resource_segment}"
                else:
                    # Fallback for unexpected structure
                    return "/api/v1/securities/unknown"
            
            # Longer paths - likely nested resources
            elif len(parts) > 6:
                # Check if second segment looks like ID
                if len(parts) > 4 and self._looks_like_id(parts[4]):
                    # Build pattern with ID parameterization
                    pattern_parts = ["/api/v1/securities/{id}"]
                    pattern_parts.extend(parts[5:])
                    return "/".join(pattern_parts)
                else:
                    return "/api/v1/securities/unknown"
            
            # Fallback for unexpected structures
            else:
                return "/api/v1/securities/unknown"
                
        except Exception as e:
            logger.error(
                "Failed to extract v1 securities pattern",
                extra={"path": path, "error": str(e), "error_type": type(e).__name__}
            )
            return "/api/v1/securities/unknown"
    
    def _extract_securities_v2_pattern(self, path: str) -> str:
        """
        Extract route patterns for /api/v2/securities endpoints.
        
        Handles the v2 securities API patterns:
        - /api/v2/securities/search -> /api/v2/securities/search
        - /api/v2/securities/{id}/details -> /api/v2/securities/{id}/details
        - /api/v2/securities/{id} -> /api/v2/securities/{id}
        
        Args:
            path: Normalized path starting with /api/v2/securities
            
        Returns:
            Route pattern for v2 securities endpoints
        """
        try:
            parts = path.split("/")
            
            # /api/v2/securities (base endpoint)
            if len(parts) == 4:  # ['', 'api', 'v2', 'securities']
                return "/api/v2/securities"
            
            # /api/v2/securities/something
            elif len(parts) == 5:
                segment = parts[4]
                
                # Known static endpoints
                if segment in ["search", "advanced-search", "bulk", "export"]:
                    return f"/api/v2/securities/{segment}"
                
                # Dynamic ID endpoint
                elif self._looks_like_id(segment):
                    return "/api/v2/securities/{id}"
                
                # Unknown segment - treat as static endpoint
                else:
                    return f"/api/v2/securities/{segment}"
            
            # /api/v2/securities/{id}/something (nested resources)
            elif len(parts) == 6:
                id_segment = parts[4]
                resource_segment = parts[5]
                
                # Verify the middle segment looks like an ID
                if self._looks_like_id(id_segment):
                    # Known nested resources
                    if resource_segment in ["details", "summary", "analytics", "related"]:
                        return f"/api/v2/securities/{{id}}/{resource_segment}"
                    else:
                        return f"/api/v2/securities/{{id}}/{resource_segment}"
                else:
                    # Static endpoint with sub-resource
                    return f"/api/v2/securities/{id_segment}/{resource_segment}"
            
            # Longer paths - handle nested resources
            elif len(parts) > 6:
                # Check if second segment looks like ID
                if len(parts) > 4 and self._looks_like_id(parts[4]):
                    # Build pattern with ID parameterization
                    pattern_parts = ["/api/v2/securities/{id}"]
                    pattern_parts.extend(parts[5:])
                    return "/".join(pattern_parts)
                else:
                    # Static nested endpoint
                    pattern_parts = ["/api/v2/securities"]
                    pattern_parts.extend(parts[4:])
                    return "/".join(pattern_parts)
            
            # Fallback for unexpected structures
            else:
                return "/api/v2/securities/unknown"
                
        except Exception as e:
            logger.error(
                "Failed to extract v2 securities pattern",
                extra={"path": path, "error": str(e), "error_type": type(e).__name__}
            )
            return "/api/v2/securities/unknown"
    
    def _extract_health_pattern(self, path: str) -> str:
        """
        Extract route patterns for /health endpoints.
        
        Handles health check patterns:
        - /health -> /health
        - /health/live -> /health/{check_type}
        - /health/ready -> /health/{check_type}
        - /health/metrics -> /health/{check_type}
        
        Args:
            path: Normalized path starting with /health
            
        Returns:
            Route pattern for health endpoints
        """
        try:
            parts = path.split("/")
            
            # /health (base health endpoint)
            if len(parts) == 2:  # ['', 'health']
                return "/health"
            
            # /health/something
            elif len(parts) == 3:
                check_type = parts[2]
                
                # Known health check types
                if check_type in ["live", "ready", "startup", "metrics", "status"]:
                    return "/health/{check_type}"
                
                # Unknown health check type - still parameterize
                else:
                    return "/health/{check_type}"
            
            # Longer health paths (unusual but handle gracefully)
            elif len(parts) > 3:
                # Parameterize the first sub-path and keep the rest
                pattern_parts = ["/health/{check_type}"]
                pattern_parts.extend(parts[3:])
                return "/".join(pattern_parts)
            
            # Fallback
            else:
                return "/health/unknown"
                
        except Exception as e:
            logger.error(
                "Failed to extract health pattern",
                extra={"path": path, "error": str(e), "error_type": type(e).__name__}
            )
            return "/health/unknown"
    
    def _sanitize_unmatched_route(self, path: str) -> str:
        """
        Sanitize unmatched routes with ID detection and parameterization.
        
        This method handles routes that don't match known patterns by:
        1. Detecting segments that look like IDs and parameterizing them
        2. Limiting path depth to prevent unbounded cardinality
        3. Sanitizing potentially problematic characters
        
        Args:
            path: Original path that didn't match known patterns
            
        Returns:
            Sanitized route pattern with ID parameterization
        """
        try:
            # Handle empty or problematic paths
            if not path:
                return "/unknown"
            
            # Remove query parameters and fragments
            clean_path = path.split("?")[0].split("#")[0]
            
            # Remove trailing slash for consistent processing
            clean_path = clean_path.rstrip("/")
            if not clean_path:
                return "/"
            
            parts = clean_path.split("/")
            
            # Limit path depth to prevent cardinality explosion (max 5 segments)
            if len(parts) > 6:  # [''] + 5 actual segments
                parts = parts[:6]
                logger.debug(
                    "Truncated long path to prevent high cardinality",
                    extra={"original_path": path, "truncated_parts": len(parts)}
                )
            
            # Process each path segment
            sanitized_parts = []
            for i, part in enumerate(parts):
                if i == 0:  # Skip empty first part from leading slash
                    sanitized_parts.append(part)
                    continue
                
                # Check if this segment looks like an ID
                if self._looks_like_id(part):
                    # Parameterize based on context or position
                    if i > 1 and "user" in parts[i-1].lower():
                        sanitized_parts.append("{user_id}")
                    elif i > 1 and "account" in parts[i-1].lower():
                        sanitized_parts.append("{account_id}")
                    else:
                        sanitized_parts.append("{id}")
                else:
                    # Keep non-ID segments but sanitize them
                    sanitized_part = self._sanitize_path_segment(part)
                    sanitized_parts.append(sanitized_part)
            
            result = "/".join(sanitized_parts)
            
            # Ensure we don't return empty string
            if not result or result == "/":
                return "/"
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to sanitize unmatched route",
                extra={"path": path, "error": str(e), "error_type": type(e).__name__}
            )
            return "/unknown"
    
    def _looks_like_id(self, segment: str) -> bool:
        """
        Determine if a path segment looks like an identifier.
        
        Detects various ID formats commonly used in APIs:
        - MongoDB ObjectIds (24 hex characters)
        - UUIDs (with or without hyphens)
        - Numeric IDs
        - Short alphanumeric codes
        
        Args:
            segment: Path segment to analyze
            
        Returns:
            True if segment appears to be an identifier
        """
        try:
            if not segment or len(segment) < 2:
                return False
            
            # Common non-ID words that should never be treated as IDs
            common_words = {
                'accounts', 'users', 'settings', 'profile', 'details', 'history',
                'search', 'advanced-search', 'bulk', 'export', 'summary', 'analytics',
                'related', 'live', 'ready', 'startup', 'metrics', 'status', 'health',
                'api', 'docs', 'openapi', 'swagger', 'admin', 'public', 'private',
                'create', 'update', 'delete', 'list', 'view', 'edit', 'new'
            }
            
            if segment.lower() in common_words:
                return False
            
            # MongoDB ObjectId pattern (24 hex characters)
            if len(segment) == 24:
                if all(c in "0123456789abcdefABCDEF" for c in segment):
                    return True
                else:
                    # 24 characters but not all hex - likely malformed ObjectId, not an ID
                    return False
            
            # UUID patterns (with or without hyphens)
            if len(segment) == 36 and segment.count("-") == 4:
                # Standard UUID format: 8-4-4-4-12
                uuid_parts = segment.split("-")
                if (len(uuid_parts) == 5 and 
                    len(uuid_parts[0]) == 8 and len(uuid_parts[1]) == 4 and 
                    len(uuid_parts[2]) == 4 and len(uuid_parts[3]) == 4 and 
                    len(uuid_parts[4]) == 12):
                    return all(all(c in "0123456789abcdefABCDEF" for c in part) for part in uuid_parts)
            
            # UUID without hyphens (32 hex characters)
            if len(segment) == 32 and all(c in "0123456789abcdefABCDEF" for c in segment):
                return True
            
            # Check for malformed ObjectId-like strings (close to 24 chars, mostly hex)
            # These should NOT be treated as IDs since they're likely malformed
            if 20 <= len(segment) <= 30:
                hex_chars = sum(1 for c in segment if c in "0123456789abcdefABCDEF")
                total_chars = len(segment)
                # If it's mostly hex (>80%) but not exactly 24 or 32 chars, it's likely malformed
                if hex_chars / total_chars > 0.8 and len(segment) not in [24, 32]:
                    return False
            
            # Numeric IDs (integers) - but not single digits which are often version numbers
            if segment.isdigit() and len(segment) >= 2:
                return True
            
            # Single digit numbers could be version numbers, so be more careful
            if segment.isdigit() and len(segment) == 1:
                return False
            
            # Short alphanumeric codes (likely IDs if 8-20 chars and mixed case/numbers)
            # Made more restrictive to avoid false positives
            if (8 <= len(segment) <= 20 and 
                segment.isalnum() and 
                any(c.isdigit() for c in segment) and 
                any(c.isalpha() for c in segment) and
                not segment.lower() in common_words):
                # Additional check: if it looks like a malformed ObjectId/UUID (mostly hex, wrong length)
                # we should be more careful. But normal mixed alphanumeric should still work.
                if all(c in "0123456789abcdefABCDEF" for c in segment):
                    # If it's all hex characters, check if it's a reasonable ID length
                    # Allow common ID lengths but reject obvious malformed ObjectId/UUID lengths
                    if len(segment) in [23, 25, 26, 27, 28, 29, 30, 31, 33, 34, 35]:
                        # These lengths are suspicious for hex-only strings (close to ObjectId/UUID)
                        return False
                    # Other hex lengths (8-22, 24, 32) are acceptable
                    return True
                # For non-hex alphanumeric, apply the original logic
                return True
            
            # Base64-like patterns (common in some ID schemes) - more restrictive
            if (len(segment) >= 12 and len(segment) <= 32 and
                all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in segment)):
                # Must have some variety in characters to be considered base64
                unique_chars = set(segment.replace("=", ""))
                if len(unique_chars) >= 4:  # At least 4 different characters
                    return True
            
            return False
            
        except Exception as e:
            logger.error(
                "Error in ID detection",
                extra={"segment": segment, "error": str(e), "error_type": type(e).__name__}
            )
            # When in doubt, assume it's not an ID to avoid over-parameterization
            return False
    
    def _sanitize_path_segment(self, segment: str) -> str:
        """
        Sanitize a path segment to prevent problematic characters in metrics.
        
        Removes or replaces characters that could cause issues in metric labels
        while preserving the essential meaning of the path segment.
        
        Args:
            segment: Path segment to sanitize
            
        Returns:
            Sanitized path segment
        """
        try:
            if not segment:
                return "empty"
            
            # Replace problematic characters with safe alternatives
            # Keep alphanumeric, hyphens, underscores, and dots
            sanitized = ""
            for char in segment:
                if char.isalnum() or char in "-_.":
                    sanitized += char
                elif char in " \t":
                    sanitized += "_"
                else:
                    # Skip other problematic characters
                    continue
            
            # Ensure we don't return empty string
            if not sanitized:
                return "unknown"
            
            # Limit length to prevent extremely long segments
            if len(sanitized) > 50:
                sanitized = sanitized[:47] + "..."
                logger.debug(
                    "Truncated long path segment",
                    extra={"original": segment, "truncated": sanitized}
                )
            
            return sanitized
            
        except Exception as e:
            logger.error(
                "Failed to sanitize path segment",
                extra={"segment": segment, "error": str(e), "error_type": type(e).__name__}
            )
            return "unknown"
    
    def _get_method_label(self, method: str) -> str:
        """
        Convert HTTP method to uppercase string for consistent labeling.
        
        Validates the method against known HTTP methods and provides
        consistent error handling for invalid values. Ensures all
        metrics use standardized method labels.
        
        Args:
            method: HTTP method string (e.g., 'get', 'POST', 'Put')
            
        Returns:
            Uppercase method string (e.g., 'GET', 'POST', 'PUT')
            Returns 'UNKNOWN' for invalid or missing methods
        """
        try:
            # Handle None or empty method
            if not method:
                logger.debug("Empty or None method provided, using UNKNOWN")
                return "UNKNOWN"
            
            # Convert to uppercase and strip whitespace
            normalized_method = str(method).strip().upper()
            
            # Validate against known HTTP methods
            valid_methods = {
                'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 
                'TRACE', 'CONNECT', 'PROPFIND', 'PROPPATCH', 'MKCOL', 
                'COPY', 'MOVE', 'LOCK', 'UNLOCK'
            }
            
            if normalized_method in valid_methods:
                logger.debug(f"Valid HTTP method normalized: {method} -> {normalized_method}")
                return normalized_method
            else:
                logger.warning(
                    "Unknown HTTP method encountered",
                    extra={"original_method": method, "normalized_method": normalized_method}
                )
                return "UNKNOWN"
                
        except Exception as e:
            logger.error(
                "Failed to format method label",
                extra={
                    "method": method, 
                    "error": str(e), 
                    "error_type": type(e).__name__
                }
            )
            return "UNKNOWN"
    
    def _format_status_code(self, status_code: Union[int, str]) -> str:
        """
        Convert numeric status code to string for consistent labeling.
        
        Validates the status code against valid HTTP status code ranges
        and provides consistent error handling for invalid values. Ensures
        all metrics use standardized status code labels.
        
        Args:
            status_code: HTTP status code as integer or string
            
        Returns:
            Status code as string (e.g., '200', '404', '500')
            Returns '500' for invalid status codes
        """
        try:
            # Handle None or empty status code
            if status_code is None:
                logger.debug("None status code provided, using 500")
                return "500"
            
            # Convert to integer first for validation
            if isinstance(status_code, str):
                # Handle empty string
                if not status_code.strip():
                    logger.debug("Empty status code string provided, using 500")
                    return "500"
                
                # Try to convert string to integer
                try:
                    status_int = int(status_code.strip())
                except ValueError:
                    logger.warning(
                        "Invalid status code string format",
                        extra={"status_code": status_code}
                    )
                    return "500"
            elif isinstance(status_code, (int, float)):
                status_int = int(status_code)
            else:
                logger.warning(
                    "Unexpected status code type",
                    extra={"status_code": status_code, "type": type(status_code).__name__}
                )
                return "500"
            
            # Validate status code range (HTTP status codes are 100-599)
            if 100 <= status_int <= 599:
                status_str = str(status_int)
                logger.debug(f"Valid status code formatted: {status_code} -> {status_str}")
                return status_str
            else:
                logger.warning(
                    "Status code outside valid HTTP range (100-599)",
                    extra={"status_code": status_code, "parsed_int": status_int}
                )
                # Return appropriate default based on range
                if status_int < 100:
                    return "500"  # Treat as server error
                elif status_int >= 600:
                    return "500"  # Treat as server error
                else:
                    return "500"  # Fallback
                    
        except Exception as e:
            logger.error(
                "Failed to format status code",
                extra={
                    "status_code": status_code,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return "500"

def setup_monitoring(app):
    """
    Setup monitoring and observability for the FastAPI application.
    
    This function configures additional monitoring components that complement
    the EnhancedHTTPMetricsMiddleware. It attempts to use prometheus-fastapi-instrumentator
    if available, but provides graceful fallback if not installed.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Configured instrumentator instance if available, None otherwise
    """
    try:
        # Try to import prometheus-fastapi-instrumentator
        from prometheus_fastapi_instrumentator import Instrumentator, metrics
        
        logger.info("Setting up prometheus-fastapi-instrumentator")
        
        # Create instrumentator with minimal conflicting metrics
        # We disable most default metrics to avoid conflicts with our custom middleware
        instrumentator = Instrumentator(
            should_group_status_codes=False,  # We handle status codes in our middleware
            should_ignore_untemplated=True,   # Ignore untemplated routes to reduce cardinality
            should_respect_env_var=True,      # Respect ENABLE_METRICS env var
            should_instrument_requests_inprogress=False,  # We handle in-flight in our middleware
            should_instrument_requests_size=True,         # This doesn't conflict
            should_instrument_responses_size=True,        # This doesn't conflict
            excluded_handlers=["/metrics"],   # Don't instrument the metrics endpoint itself
            env_var_name="ENABLE_METRICS",   # Environment variable to control instrumentation
            inprogress_name="http_requests_inprogress_instrumentator",  # Different name to avoid conflict
            inprogress_labels=True
        )
        
        # Add only non-conflicting metrics that complement our custom middleware
        # These provide additional insights without duplicating our core metrics
        try:
            # Request/response size metrics (these don't conflict with our middleware)
            instrumentator.add(metrics.combined_size())
            logger.debug("Added combined size metrics to instrumentator")
        except Exception as e:
            logger.warning(f"Failed to add combined size metrics: {e}")
        
        try:
            # Add custom metric for tracking instrumentator health
            instrumentator.add(
                metrics.default(
                    metric_name="instrumentator_requests_total",
                    metric_doc="Total requests tracked by instrumentator (for validation)",
                    metric_namespace="",
                    metric_subsystem=""
                )
            )
            logger.debug("Added instrumentator validation metrics")
        except Exception as e:
            logger.warning(f"Failed to add instrumentator validation metrics: {e}")
        
        # Instrument the app
        instrumentator.instrument(app)
        logger.info("FastAPI instrumentator setup complete")
        
        return instrumentator
        
    except ImportError:
        logger.info(
            "prometheus-fastapi-instrumentator not available, "
            "using only custom EnhancedHTTPMetricsMiddleware"
        )
        return None
        
    except Exception as e:
        logger.error(
            "Failed to setup prometheus-fastapi-instrumentator",
            extra={"error": str(e), "error_type": type(e).__name__}
        )
        return None


def get_monitoring_status() -> Dict[str, Any]:
    """
    Get the current status of the monitoring system.
    
    Returns comprehensive information about the monitoring setup including
    metrics registry status, OpenTelemetry availability, and instrumentator status.
    
    Returns:
        Dictionary containing monitoring system status information
    """
    try:
        status = {
            "enhanced_middleware_available": True,
            "metrics_registry_info": get_metrics_registry_info(),
            "opentelemetry_available": OTEL_AVAILABLE,
            "opentelemetry_meter_initialized": otel_meter is not None,
            "prometheus_metrics_available": True,
            "timestamp": time.time()
        }
        
        # Check if instrumentator is available
        try:
            from prometheus_fastapi_instrumentator import Instrumentator
            status["instrumentator_available"] = True
        except ImportError:
            status["instrumentator_available"] = False
        
        # Check metrics health
        try:
            # Test if we can create a simple metric
            test_counter = _get_or_create_metric(
                Counter,
                'monitoring_health_check',
                'Health check counter for monitoring system'
            )
            test_counter.inc(0)  # Increment by 0 to test functionality
            status["metrics_creation_healthy"] = True
        except Exception as e:
            status["metrics_creation_healthy"] = False
            status["metrics_creation_error"] = str(e)
        
        # Check OpenTelemetry health
        if otel_meter:
            try:
                # Test OpenTelemetry metric creation
                test_otel_counter = otel_meter.create_counter(
                    name="monitoring_health_check_otel",
                    description="Health check counter for OpenTelemetry"
                )
                test_otel_counter.add(0)  # Add 0 to test functionality
                status["opentelemetry_healthy"] = True
            except Exception as e:
                status["opentelemetry_healthy"] = False
                status["opentelemetry_error"] = str(e)
        else:
            status["opentelemetry_healthy"] = False
            status["opentelemetry_error"] = "OpenTelemetry meter not initialized"
        
        return status
        
    except Exception as e:
        logger.error(
            "Failed to get monitoring status",
            extra={"error": str(e), "error_type": type(e).__name__}
        )
        return {
            "enhanced_middleware_available": False,
            "error": str(e),
            "timestamp": time.time()
        }


def configure_metrics_endpoint(app, path: str = "/metrics"):
    """
    Configure the Prometheus metrics endpoint for the FastAPI application.
    
    This function adds a /metrics endpoint that exposes Prometheus metrics
    in the standard format. It uses the prometheus_client's make_asgi_app()
    to create a proper ASGI application for serving metrics.
    
    Args:
        app: FastAPI application instance
        path: Path where metrics endpoint should be mounted (default: "/metrics")
    """
    try:
        from prometheus_client import make_asgi_app
        
        # Create Prometheus ASGI app
        metrics_app = make_asgi_app()
        
        # Mount the metrics app at the specified path
        app.mount(path, metrics_app)
        
        logger.info(f"Prometheus metrics endpoint configured at {path}")
        
    except ImportError as e:
        logger.error(
            "Failed to configure metrics endpoint: prometheus_client not available",
            extra={"error": str(e)}
        )
        raise
        
    except Exception as e:
        logger.error(
            "Failed to configure metrics endpoint",
            extra={"error": str(e), "error_type": type(e).__name__, "path": path}
        )
        raise


def validate_monitoring_setup(app) -> Dict[str, Any]:
    """
    Validate that the monitoring setup is working correctly.
    
    This function performs comprehensive validation of the monitoring system
    including middleware registration, metrics creation, and endpoint availability.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Dictionary containing validation results and any issues found
    """
    validation_results = {
        "timestamp": time.time(),
        "overall_status": "unknown",
        "checks": {},
        "issues": [],
        "recommendations": []
    }
    
    try:
        # Check 1: Middleware registration
        middleware_found = False
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'EnhancedHTTPMetricsMiddleware':
                middleware_found = True
                break
        
        validation_results["checks"]["middleware_registered"] = middleware_found
        if not middleware_found:
            validation_results["issues"].append("EnhancedHTTPMetricsMiddleware not found in app middleware")
            validation_results["recommendations"].append("Add EnhancedHTTPMetricsMiddleware to your FastAPI app")
        
        # Check 2: Metrics registry health
        registry_info = get_metrics_registry_info()
        validation_results["checks"]["metrics_registry"] = registry_info
        
        if registry_info["prometheus_metrics_count"] == 0:
            validation_results["issues"].append("No Prometheus metrics found in registry")
            validation_results["recommendations"].append("Ensure HTTP metrics are being created during app startup")
        
        # Check 3: OpenTelemetry status
        validation_results["checks"]["opentelemetry_status"] = {
            "available": OTEL_AVAILABLE,
            "meter_initialized": otel_meter is not None
        }
        
        if not OTEL_AVAILABLE:
            validation_results["recommendations"].append(
                "Install OpenTelemetry packages for dual metrics export capability"
            )
        
        # Check 4: Routes inspection
        routes_with_metrics = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes_with_metrics.append({
                    "path": route.path,
                    "methods": getattr(route, 'methods', [])
                })
        
        validation_results["checks"]["routes_count"] = len(routes_with_metrics)
        validation_results["checks"]["sample_routes"] = routes_with_metrics[:5]  # First 5 routes
        
        # Determine overall status
        if len(validation_results["issues"]) == 0:
            validation_results["overall_status"] = "healthy"
        elif middleware_found and registry_info["prometheus_metrics_count"] > 0:
            validation_results["overall_status"] = "functional_with_warnings"
        else:
            validation_results["overall_status"] = "unhealthy"
        
        logger.info(
            f"Monitoring validation complete: {validation_results['overall_status']}",
            extra={
                "issues_count": len(validation_results["issues"]),
                "middleware_found": middleware_found,
                "metrics_count": registry_info["prometheus_metrics_count"]
            }
        )
        
        return validation_results
        
    except Exception as e:
        validation_results["overall_status"] = "error"
        validation_results["issues"].append(f"Validation failed: {str(e)}")
        
        logger.error(
            "Monitoring validation failed",
            extra={"error": str(e), "error_type": type(e).__name__}
        )
        
        return validation_results