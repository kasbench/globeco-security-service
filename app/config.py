from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    MONGODB_URI: str = Field(default="mongodb://globeco-security-service-mongodb:27017", env="MONGODB_URI")
    MONGODB_DB: str = Field(default="securities", env="MONGODB_DB")  # Database for GlobeCo Security Service
    # OpenTelemetry settings
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="otel-collector-collector.monitoring.svc.cluster.local:4317", env="OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_SERVICE_NAME: str = Field(default="globeco-security-service", env="OTEL_SERVICE_NAME")
    OTEL_EXPORTER_OTLP_INSECURE: bool = Field(default=True, env="OTEL_EXPORTER_OTLP_INSECURE")
    # Metrics settings
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")

settings = Settings()
