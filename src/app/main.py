from datetime import datetime

from fastapi import FastAPI

from app.routes import router as rate_car_router

app = FastAPI()
app.include_router(rate_car_router)


@app.get("/health")
def health() -> dict[str, str | datetime]:
    return {"status": "ok", "timestamp": datetime.now()}
