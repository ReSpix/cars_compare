# Cars Compare API

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --app-dir src --reload
```

The health endpoint is available at [http://localhost:8000/health](http://localhost:8000/health).

## Run with Docker Compose

```bash
docker compose up --build
```

The API is available at [http://localhost:8000/health](http://localhost:8000/health).
