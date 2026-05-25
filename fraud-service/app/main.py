from fastapi import FastAPI

from app.core.startup import lifespan
from app.api.routes.health_routes import router as health_router
from app.api.routes.order_routes import router as order_router
from app.observability.telemetry import setup_telemetry, instrument_app
from app.core.settings import settings

setup_telemetry(
    otlp_endpoint = settings.otlp_endpoint
)

app = FastAPI(
    title = "Fraud Service",
    lifespan = lifespan,
    root_path = "/fraud",
)

instrument_app(app)

app.include_router(health_router)
app.include_router(order_router)