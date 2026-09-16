"""A small FastAPI service designed for observability practice."""

import asyncio
import os
import time

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = FastAPI(title="AIOps Orders API", version="1.0.0")

REQUESTS = Counter(
    "demo_api_http_requests_total",
    "Total HTTP requests handled by the demo API.",
    ["method", "route", "status_code"],
)
REQUEST_DURATION = Histogram(
    "demo_api_http_request_duration_seconds",
    "HTTP request duration handled by the demo API.",
    ["method", "route", "status_code"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)


def configure_tracing() -> None:
    """Export traces only when an OTLP endpoint is explicitly configured."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return

    resource = Resource.create({SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "orders-api")})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    """Record request count and duration after the response is known."""
    if request.url.path in {"/metrics", "/health"}:
        return await call_next(request)

    started = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - started
    route = request.scope.get("route")
    route_name = getattr(route, "path", request.url.path)
    labels = {
        "method": request.method,
        "route": route_name,
        "status_code": str(response.status_code),
    }
    REQUESTS.labels(**labels).inc()
    REQUEST_DURATION.labels(**labels).observe(duration)
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        response.headers["X-Trace-Id"] = f"{span_context.trace_id:032x}"
    return response


@app.get("/")
async def root():
    return {"service": "aiops-orders-api", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/orders")
async def list_orders(
    fail: bool = Query(False, description="Return a deliberate HTTP 500 for the lab."),
    delay_ms: int = Query(0, ge=0, le=5000, description="Add controlled latency in milliseconds."),
):
    if delay_ms:
        await asyncio.sleep(delay_ms / 1000)
    if fail:
        return JSONResponse(status_code=500, content={"detail": "simulated orders dependency failure"})
    return {"orders": [{"id": "order-1001", "status": "created"}]}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


configure_tracing()
