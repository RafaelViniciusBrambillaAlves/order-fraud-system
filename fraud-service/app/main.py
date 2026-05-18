from fastapi import FastAPI

from app.core.startup import lifespan
from app.api.routes.health_routes import router as health_router
from app.api.routes.order_routes import router as order_router



app = FastAPI(
    title = "Fraud Service",
    lifespan = lifespan,
    root_path = "/fraud",
)

app.include_router(health_router)
app.include_router(order_router)