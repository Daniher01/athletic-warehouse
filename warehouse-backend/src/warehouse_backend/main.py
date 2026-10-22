from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from warehouse_backend.config import settings
from warehouse_backend.presentation.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup actions
    yield
    # Shutdown actions


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        lifespan=lifespan,
    )
    application.include_router(api_v1_router)
    return application


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("warehouse_backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
