# Requirements Document

## Introduction

This feature implements standardized HTTP request metrics for the GlobeCo Security Service microservice that can be exported to the OpenTelemetry (Otel) Collector. The implementation will provide consistent observability across services by collecting three core HTTP metrics: request totals, request duration, and in-flight requests. Based on lessons learned from previous implementations, this will use a dual metrics system with both Prometheus (for /metrics endpoint) and OpenTelemetry (for collector export) to ensure metrics appear in the monitoring infrastructure regardless of collection method.

## Requirements

### Requirement 1

**User Story:** As a DevOps engineer, I want to monitor HTTP request patterns across all microservices, so that I can identify performance bottlenecks and service health issues.

#### Acceptance Criteria

1. WHEN an HTTP request is made to any endpoint THEN the system SHALL increment the `http_requests_total` counter with labels for method, path, and status
2. WHEN an HTTP request is completed THEN the system SHALL record the request duration in the `http_request_duration` histogram with the same labels
3. WHEN an HTTP request begins processing THEN the system SHALL increment the `http_requests_in_flight` gauge
4. WHEN an HTTP request completes (success or failure) THEN the system SHALL decrement the `http_requests_in_flight` gauge

### Requirement 2

**User Story:** As a platform engineer, I want HTTP metrics to be available through both Prometheus scraping and OpenTelemetry collection, so that metrics appear in our monitoring system regardless of the collection method used.

#### Acceptance Criteria

1. WHEN the `/metrics` endpoint is accessed THEN the system SHALL return Prometheus-formatted HTTP metrics
2. WHEN the OpenTelemetry collector scrapes the service THEN the system SHALL export identical HTTP metrics via OTLP
3. WHEN both collection methods are active THEN the metric values SHALL be identical between Prometheus and OpenTelemetry systems
4. IF OpenTelemetry metric recording fails THEN the system SHALL continue processing requests and log the error

**IMPORTANT NOTE** This service feeds metrics to the OpenTelemetry Collector.  The /metrics endpoint is for debugging purposes only.  The only change to feeding metrics to the OpenTelemetry Collector should be to add the new custom metrics.

### Requirement 3

**User Story:** As a monitoring engineer, I want HTTP metrics to use consistent labeling and prevent high cardinality, so that the metrics system remains performant and storage costs are controlled.

#### Acceptance Criteria

1. WHEN recording HTTP method labels THEN the system SHALL use uppercase format (GET, POST, PUT, DELETE, etc.)
2. WHEN recording path labels THEN the system SHALL use route patterns instead of actual URLs with parameters (e.g., "/api/v1/securities/{id}" instead of "/api/v1/securities/123")
3. WHEN recording status labels THEN the system SHALL convert numeric status codes to strings ("200", "404", "500")
4. WHEN encountering unknown routes THEN the system SHALL sanitize them to prevent unbounded label cardinality
5. WHEN a path contains identifiers THEN the system SHALL parameterize them using patterns like {id}, {user_id}, etc.

### Requirement 4

**User Story:** As a service developer, I want HTTP metrics collection to not interfere with normal request processing, so that application performance and reliability are maintained.

#### Acceptance Criteria

1. WHEN metrics recording fails THEN the system SHALL continue processing the HTTP request normally
2. WHEN metrics recording encounters an error THEN the system SHALL log the error with structured logging
3. WHEN timing HTTP requests THEN the system SHALL use high-precision timing (microsecond accuracy)
4. WHEN processing requests THEN the metrics collection overhead SHALL be minimal and not impact response times significantly

### Requirement 5

**User Story:** As a service operator, I want HTTP metrics to cover all endpoints including health checks and error responses, so that I have complete visibility into service behavior.

#### Acceptance Criteria

1. WHEN any HTTP endpoint is accessed THEN the system SHALL record metrics regardless of the endpoint type (API, health, static files)
2. WHEN HTTP requests result in errors (4xx, 5xx) THEN the system SHALL still record all three metrics with appropriate status labels
3. WHEN HTTP requests result in exceptions THEN the system SHALL record metrics with status "500" before re-raising the exception
4. WHEN the service starts up THEN the system SHALL initialize all metrics to ensure they appear in exports even before first use

### Requirement 6

**User Story:** As a deployment engineer, I want the metrics implementation to work with single-process deployments, so that metric counts are consistent and accurate.

#### Acceptance Criteria

1. WHEN the service is deployed THEN it SHALL use single-process configuration (Uvicorn) to ensure consistent metrics
2. WHEN multiple requests are processed concurrently THEN the in-flight gauge SHALL accurately track concurrent request count
3. WHEN the service restarts THEN metrics SHALL reset to zero and begin counting from startup
4. IF multi-worker deployment is attempted THEN the system SHALL provide clear documentation about metrics inconsistency risks

### Requirement 7

**User Story:** As a service maintainer, I want HTTP metrics to be easily testable and debuggable, so that I can verify correct implementation and troubleshoot issues.

#### Acceptance Criteria

1. WHEN debug logging is enabled THEN the system SHALL log detailed metrics recording information
2. WHEN unit tests are run THEN the system SHALL not attempt external network connections for metrics export
3. WHEN integration tests are run THEN the system SHALL verify both Prometheus and OpenTelemetry metrics are recorded
4. WHEN the service is running THEN health endpoints SHALL include current in-flight request count for debugging

### Requirement 8

**User Story:** As a security service developer, I want route patterns to be customized for our specific API endpoints, so that metrics accurately reflect our service's URL structure.

#### Acceptance Criteria

1. WHEN requests are made to `/api/v1/securities/{id}` endpoints THEN the system SHALL use the pattern `/api/v1/securities/{id}` in metrics
2. WHEN requests are made to `/api/v2/securities/search` endpoints THEN the system SHALL use the exact path in metrics
3. WHEN requests are made to health check endpoints THEN the system SHALL use patterns like `/health/{check_type}` for sub-endpoints
4. WHEN requests are made to unknown endpoints THEN the system SHALL sanitize them to prevent high cardinality while maintaining useful information