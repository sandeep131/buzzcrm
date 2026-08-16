"""FastAPI application factory."""

from fastapi import FastAPI

from src.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe. Deliberately does not touch the database —
        it answers 'is the process up', not 'is everything healthy'."""
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
