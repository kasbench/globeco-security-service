from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application configuration settings.
    
    All settings can be overridden using environment variables.
    """
    
    # Database settings
    MONGODB_URI: str = Field(
        default="mongodb://globeco-security-service-mongodb:27017", 
        env="MONGODB_URI",
        description="MongoDB connection URI"
    )
    MONGODB_DB: str = Field(
        default="securities", 
        env="MONGODB_DB",
        description="Database name for GlobeCo Security Service"
    )
    
    # OpenTelemetry settings
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default="otel-collector-collector.monitoring.svc.cluster.local:4317", 
        env="OTEL_EXPORTER_OTLP_ENDPOINT",
        description="OpenTelemetry collector endpoint for metrics export"
    )
    OTEL_SERVICE_NAME: str = Field(
        default="globeco-security-service", 
        env="OTEL_SERVICE_NAME",
        description="Service name for OpenTelemetry identification"
    )
    OTEL_EXPORTER_OTLP_INSECURE: bool = Field(
        default=True, 
        env="OTEL_EXPORTER_OTLP_INSECURE",
        description="Whether to use insecure connection to OpenTelemetry collector"
    )
    
    # Metrics settings
    enable_metrics: bool = Field(
        default=True, 
        env="ENABLE_METRICS",
        description="Enable HTTP metrics collection and export. When True, collects request totals, duration, and in-flight metrics for both Prometheus (/metrics endpoint) and OpenTelemetry export to collector."
    )

settings = Settings()
