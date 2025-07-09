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
import os
from fastapi.middleware.cors import CORSMiddleware
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
            endpoint=f"http://{settings.OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics"
        )
    )
]
meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
set_meter_provider(meter_provider)

# --- FastAPI app instantiation ---
app = FastAPI(title="GlobeCo Security Service", version="1.0.0")

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

@app.on_event("startup")
async def on_startup():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]
    await init_beanie(database=db, document_models=[SecurityType, Security])
    
    # Create indexes for optimal search performance
    try:
        await Security.get_motor_collection().create_index("ticker")  # For exact matches
        await Security.get_motor_collection().create_index([("ticker", "text")])  # For text search
    except Exception as e:
        print(f"Index creation failed: {e}")  # Non-fatal for development

app.include_router(api_router)
app.include_router(v2_api_router)
app.include_router(health_router)

if os.environ.get("TEST_MODE") == "1":
    from app.api.utils_routes import router as test_utils_router
    app.include_router(test_utils_router)

if __name__ == "__main__":
    asyncio.run(on_startup())
