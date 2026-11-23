from datetime import datetime

from fastapi import FastAPI

from app.api.auctions import router as auctions_router
from app.api.car_rate import router as rate_car_router
from app.api.shared import router as shared_api_router

app = FastAPI()
app.include_router(auctions_router)
app.include_router(rate_car_router)
app.include_router(shared_api_router)


@app.get("/health")
def health() -> dict[str, str | datetime]:
    return {"status": "ok", "timestamp": datetime.now()}
