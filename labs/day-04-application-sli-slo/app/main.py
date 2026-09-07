"""A small FastAPI service designed for observability practice."""

import asyncio
import time

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response
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
