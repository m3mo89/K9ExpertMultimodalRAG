from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from k9_expert.application.composition import ApplicationContainer, compose


class HealthResponse(BaseModel):
    status: str
    worker_concurrency: int


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    resolved = container or compose()
    app = FastAPI(title="K9 Expert", version="0.1.0")

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", worker_concurrency=resolved.settings.worker_concurrency)

    return app


app = create_app()

