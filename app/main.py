import asyncio
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
from app.models.security_type import SecurityType
from app.models.security import Security
from app.api.routes import router as api_router
from app.api.v2_routes import router as v2_api_router
from app.api.health import router as health_router
from app.migrations.runner import run_migrations
import os
from fastapi.middleware.cors import CORSMiddleware
# Enhanced HTTP metrics imports
from app.core.monitoring import EnhancedHTTPMetricsMiddleware, setup_monitoring
from prometheus_client import make_asgi_app, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPMetricExporterGRPC
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPMetricExporterHTTP
from opentelemetry.metrics import set_meter_provider

# Additional instrumentation imports
try:
    from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
    SYSTEM_METRICS_AVAILABLE = True
except ImportError:
    SYSTEM_METRICS_AVAILABLE = False

try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# --- OpenTelemetry setup ---
resource = Resource.create({
    "service.name": settings.OTEL_SERVICE_NAME
})

trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter = OTLPSpanExporter(
    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
    insecure=settings.OTEL_EXPORTER_OTLP_INSECURE
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# --- OpenTelemetry Metrics setup ---
metric_readers = [
    PeriodicExportingMetricReader(
        OTLPMetricExporterGRPC(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=settings.OTEL_EXPORTER_OTLP_INSECURE
        )
    ),
    PeriodicExportingMetricReader(
        OTLPMetricExporterHTTP(
            endpoint=f"http://otel-collector-daemonset-collector.monitoring.svc.cluster.local:4318/v1/metrics"
        )
    )
]
meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
set_meter_provider(meter_provider)

# Initialize additional instrumentation for standard Python metrics
if SYSTEM_METRICS_AVAILABLE:
    try:
        SystemMetricsInstrumentor().instrument()
        print("✅ System metrics instrumentation initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize system metrics: {e}")

if HTTPX_AVAILABLE:
    try:
        HTTPXClientInstrumentor().instrument()
        print("✅ HTTPX client instrumentation initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize HTTPX instrumentation: {e}")

if REQUESTS_AVAILABLE:
    try:
        RequestsInstrumentor().instrument()
        print("✅ Requests client instrumentation initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize Requests instrumentation: {e}")

# --- FastAPI app instantiation ---
app = FastAPI(title="GlobeCo Security Service", version="1.0.0")

# Setup monitoring after meter provider is initialized
if settings.enable_metrics:
    setup_monitoring(app)

# Add Enhanced HTTP Metrics Middleware first (before other middleware)
if settings.enable_metrics:
    app.add_middleware(EnhancedHTTPMetricsMiddleware)

# Instrument FastAPI for tracing
FastAPIInstrumentor.instrument_app(app)
# Optionally add ASGI middleware for context propagation
app.add_middleware(OpenTelemetryMiddleware)

# Allow all origins for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus /metrics endpoint for debugging
if settings.enable_metrics:
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint for debugging."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.on_event("startup")
async def on_startup():
    # Configure MongoDB client with connection pooling for better performance
    client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=50,           # Maximum connections in the pool
        minPoolSize=10,           # Minimum connections to maintain
        maxIdleTimeMS=45000,      # Close idle connections after 45 seconds
        waitQueueTimeoutMS=5000,  # Wait up to 5 seconds for a connection from pool
        serverSelectionTimeoutMS=5000,  # Timeout for server selection
        connectTimeoutMS=10000,   # Timeout for initial connection
        socketTimeoutMS=10000,    # Timeout for socket operations
    )
    db = client[settings.MONGODB_DB]

    # Run migrations BEFORE Beanie init
    await run_migrations(db)

    await init_beanie(database=db, document_models=[SecurityType, Security])
    
    # Create indexes for optimal search performance
    try:
        await Security.get_motor_collection().create_index("ticker")  # For exact matches
        await Security.get_motor_collection().create_index([("ticker", "text")])  # For text search
        await Security.get_motor_collection().create_index("security_type_id")  # For joins with security types
    except Exception as e:
        print(f"Index creation failed: {e}")  # Non-fatal for development
    
    # Setup monitoring and observability
    if settings.enable_metrics:
        setup_monitoring(app)

app.include_router(api_router)
app.include_router(v2_api_router)
app.include_router(health_router)

if os.environ.get("TEST_MODE") == "1":
    from app.api.utils_routes import router as test_utils_router
    app.include_router(test_utils_router)

if __name__ == "__main__":
    asyncio.run(on_startup())
