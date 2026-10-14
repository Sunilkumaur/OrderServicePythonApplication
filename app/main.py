"""
Order Service - a small sample API for learning Docker, Kubernetes (EKS) and CI/CD.

Endpoints:
  GET  /                -> welcome message
  GET  /info            -> app version, environment, and which pod answered
  GET  /health/live     -> liveness probe  ("is the process alive?")
  GET  /health/ready    -> readiness probe ("can I receive traffic?")
  GET  /orders          -> list orders
  POST /orders          -> create an order
  GET  /orders/{id}     -> get one order

Data is kept in memory on purpose: every pod has its own copy, which makes it
easy to SEE that different pods are answering behind the load balancer.
(A real service would use a database such as RDS.)
"""

import logging
import os
import socket
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# --- Configuration (comes from environment variables -> ConfigMap in Kubernetes) ---
APP_NAME = "order-service"
APP_VERSION = os.getenv("APP_VERSION", "dev")    # set by the pipeline (image tag)
APP_ENV = os.getenv("APP_ENV", "local")          # dev / test / prod
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Logging to stdout: containers should log to stdout, not to files ---
logging.basicConfig(
    stream=sys.stdout,
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger(APP_NAME)

@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("Starting %s version=%s env=%s host=%s",
             APP_NAME, APP_VERSION, APP_ENV, socket.gethostname())
    yield
    log.info("Shutting down %s", APP_NAME)   # runs on SIGTERM (pod deletion)


app = FastAPI(title="Order Service", version=APP_VERSION, lifespan=lifespan)

# In-memory "database" (per pod)
ORDERS: dict[str, dict] = {}


class OrderRequest(BaseModel):
    item: str = Field(..., min_length=1, examples=["laptop"])
    quantity: int = Field(..., gt=0, examples=[2])


@app.get("/")
def root() -> dict:
    return {"message": f"Welcome to {APP_NAME}", "docs": "/docs"}


@app.get("/info")
def info() -> dict:
    # In Kubernetes, the hostname IS the pod name -> refresh and watch it change.
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "environment": APP_ENV,
        "hostname": socket.gethostname(),
    }


@app.get("/health/live")
def liveness() -> dict:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict:
    # A real app would check its dependencies here (database, cache, ...).
    return {"status": "ready"}


@app.get("/orders")
def list_orders() -> list[dict]:
    return list(ORDERS.values())


@app.post("/orders", status_code=201)
def create_order(order: OrderRequest) -> dict:
    order_id = str(uuid4())
    record = {
        "id": order_id,
        "item": order.item,
        "quantity": order.quantity,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by_pod": socket.gethostname(),
    }
    ORDERS[order_id] = record
    log.info("Order created id=%s item=%s qty=%s", order_id, order.item, order.quantity)
    return record


@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    if order_id not in ORDERS:
        raise HTTPException(status_code=404, detail="Order not found")
    return ORDERS[order_id]
