from datetime import datetime

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str | datetime]:
    return {"status": "ok", "timestamp": datetime.now()}
