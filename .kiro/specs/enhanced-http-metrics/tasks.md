# Implementation Plan

- [x] 1. Set up core monitoring module structure
  - Create `src/core/monitoring.py` with dual metrics registry system
  - Implement `_get_or_create_metric()` utility function to prevent duplicate registration
  - Define global metrics registry dictionary for tracking created metrics
  - _Requirements: 2.1, 2.2, 4.1, 4.2_

- [x] 2. Implement Prometheus HTTP metrics
  - Create Prometheus Counter for `http_requests_total` with method, path, status labels
  - Create Prometheus Histogram for `http_request_duration` with millisecond buckets [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
  - Create Prometheus Gauge for `http_requests_in_flight` with no labels
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 3.2, 3.3_

- [x] 3. Implement OpenTelemetry HTTP metrics
  - Create OpenTelemetry Counter for `http_requests_total` using meter.create_counter()
  - Create OpenTelemetry Histogram for `http_request_duration` with millisecond unit
  - Create OpenTelemetry UpDownCounter for `http_requests_in_flight`
  - Add error handling with dummy metrics fallback for initialization failures
  - _Requirements: 2.1, 2.2, 2.3, 4.2_

- [x] 4. Create EnhancedHTTPMetricsMiddleware class
  - Implement BaseHTTPMiddleware subclass with async dispatch method
  - Add high-precision timing using time.perf_counter() for millisecond accuracy
  - Implement in-flight request tracking with proper increment/decrement in try/finally blocks
  - Add comprehensive error handling that never fails request processing
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

- [x] 5. Implement dual metrics recording system
  - Create `_record_metrics()` method that records to both Prometheus and OpenTelemetry
  - Add separate try/catch blocks for each metrics system to ensure independence
  - Include structured logging for successful recordings and failures
  - Ensure identical metric values are recorded to both systems
  - _Requirements: 2.1, 2.2, 2.3, 4.1, 4.2_

- [x] 6. Build route pattern extraction system
  - Implement `_extract_route_pattern()` method with security service specific patterns
  - Create `_extract_securities_v1_pattern()` for /api/v1/securities endpoints
  - Create `_extract_securities_v2_pattern()` for /api/v2/securities endpoints  
  - Create `_extract_health_pattern()` for /health endpoints
  - Add `_sanitize_unmatched_route()` with ID detection and parameterization
  - _Requirements: 3.2, 3.4, 3.5, 8.1, 8.2, 8.3, 8.4_

- [x] 7. Implement label formatting utilities
  - Create `_get_method_label()` to convert HTTP methods to uppercase strings
  - Create `_format_status_code()` to convert numeric status codes to strings
  - Add validation and error handling for invalid method/status values
  - Ensure consistent labeling across both metrics systems
  - _Requirements: 3.1, 3.3, 4.2_

- [x] 8. Add ID detection and parameterization logic
  - Implement `_looks_like_id()` method to identify MongoDB ObjectIds, UUIDs, and numeric IDs
  - Add logic to replace detected IDs with parameterized patterns like {id}, {user_id}
  - Handle edge cases for alphanumeric identifiers and unknown ID formats
  - Test with various ID formats used in the security service
  - _Requirements: 3.5, 8.1, 8.4_

- [x] 9. Create monitoring setup function
  - Implement `setup_monitoring()` function that configures FastAPI instrumentator
  - Add minimal conflicting metrics to avoid duplication with custom middleware
  - Configure instrumentator to exclude /metrics endpoint from its own tracking
  - Return configured instrumentator instance for application integration
  - _Requirements: 2.1, 5.4_

- [x] 10. Integrate middleware with FastAPI application
  - Modify `src/main.py` to add EnhancedHTTPMetricsMiddleware before other middleware
  - Add conditional middleware registration based on settings.enable_metrics
  - Mount Prometheus /metrics endpoint using make_asgi_app() for debugging
  - Call setup_monitoring() function during application initialization
  - _Requirements: 2.1, 5.1, 5.4, 6.1_

- [ ] 11. Add configuration settings
  - Update `src/config.py` to include enable_metrics boolean setting
  - Set default value to True for metrics collection
  - Add environment variable support for ENABLE_METRICS
  - Document configuration options in settings class
  - _Requirements: 2.1, 7.1_

- [ ] 12. Implement comprehensive error handling
  - Add try/catch blocks around all metrics recording operations
  - Implement graceful degradation when metrics systems fail
  - Add structured logging for all error conditions with context
  - Ensure request processing continues even when metrics recording fails
  - _Requirements: 4.1, 4.2, 4.3, 7.1_

- [ ] 13. Create unit tests for metrics collection
  - Write tests for EnhancedHTTPMetricsMiddleware with mocked OpenTelemetry components
  - Test route pattern extraction with security service specific URLs
  - Verify Prometheus metrics are properly incremented for various request types
  - Test error handling scenarios and ensure requests continue processing
  - _Requirements: 7.2, 7.3_

- [ ] 14. Create integration tests for dual metrics system
  - Write tests that verify both Prometheus and OpenTelemetry metrics are recorded
  - Test that metric values are identical between both systems
  - Verify /metrics endpoint returns expected Prometheus format
  - Test middleware integration with FastAPI application
  - _Requirements: 2.3, 7.3_

- [ ] 15. Add health check integration
  - Update health endpoints to include current in-flight request count
  - Add metrics initialization status to health check responses
  - Include timestamp and service information in health responses
  - Test health endpoints return correct in-flight values during load
  - _Requirements: 7.4_

- [ ] 16. Create production deployment configuration
  - Update startup script to use single-process Uvicorn deployment
  - Add environment variables for OpenTelemetry collector endpoint
  - Configure OTLP exporter settings for direct collector feeding
  - Document deployment requirements and single-process constraint
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 17. Add comprehensive logging and debugging
  - Implement debug logging for all metrics recording operations
  - Add structured logging with request context (method, path, duration, status)
  - Log slow requests (>1000ms) with warning level
  - Add metrics recording success/failure logging with error details
  - _Requirements: 4.2, 7.1_

- [ ] 18. Create validation and testing utilities
  - Write validation script to verify dual metrics system functionality
  - Create load testing scenarios to verify metrics consistency
  - Add cardinality monitoring to prevent high-cardinality metrics
  - Document testing procedures and validation steps
  - _Requirements: 7.3, 7.4_