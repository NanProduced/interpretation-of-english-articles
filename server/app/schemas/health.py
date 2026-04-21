"""Health Check API Schemas."""

from __future__ import annotations

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str
    app: str
    env: str
    postgres: bool
    redis: bool
    worker: bool
    worker_inflight_tasks: int


class DbHealthResponse(BaseModel):
    status: str
    postgres: bool


class ReadinessCheckResponse(BaseModel):
    status: str
    postgres: bool
    worker: bool
    worker_inflight_tasks: int
