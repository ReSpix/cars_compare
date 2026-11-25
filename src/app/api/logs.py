from datetime import UTC, datetime
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Body, Request, status

router = APIRouter(tags=["logs"])


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def create_log(
    message: Annotated[str, Body(media_type="text/plain")],
    request: Request,
) -> dict[str, int]:
    database: aiosqlite.Connection = request.app.state.database
    async with database.execute(
        "INSERT INTO logs (message, created_at) VALUES (?, ?)",
        (message[:2048], datetime.now(UTC).isoformat()),
    ) as cursor:
        await database.commit()
        return {"id": cursor.lastrowid}
