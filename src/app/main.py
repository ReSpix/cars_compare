import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite
from fastapi import FastAPI

from app.api.auctions import router as auctions_router
from app.api.car_rate import router as rate_car_router
from app.api.logs import router as logs_router
from app.api.shared import router as shared_api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    database_path = os.getenv("LOG_DATABASE_PATH", ":memory:")
    async with aiosqlite.connect(database_path) as database:
        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL
            )
            """
        )
        await database.commit()
        app.state.database = database
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(auctions_router)
app.include_router(rate_car_router)
app.include_router(shared_api_router)
app.include_router(logs_router)


@app.get("/health")
def health() -> dict[str, str | datetime]:
    return {"status": "ok", "timestamp": datetime.now()}
