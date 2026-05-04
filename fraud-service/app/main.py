from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading

from app.messaging.consumers.order_created_consumer import start_consumer

print("Starting Fraud Service...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target = start_consumer, daemon = True    )

    thread.start()

    yield 

app = FastAPI(lifespan = lifespan)

@app.get("/health")
def home():
    return {"message": "Fraud Service is running!"}