# Cars Compare API

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --app-dir src --reload
```

The health endpoint is available at [http://localhost:8000/health](http://localhost:8000/health).
The rate-car API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Rate-car endpoints

All parameters are passed as query parameters:

| Endpoint | Required parameters |
| --- | --- |
| `GET /rate-car/firms` | — |
| `GET /rate-car/models` | `firm_id` |
| `GET /rate-car/years` | `model_id`, `wheel` |
| `GET /rate-car/frames` | `model_id`, `year`, `wheel` |
| `GET /rate-car/generations` | `model_id`, `year`, `frame`, `wheel` |
| `GET /rate-car/modifications` | `model_id`, `year`, `frame`, `generation_id`, `wheel` |
| `GET /rate-car/price-change-chart` | `firm_id`, `model_id`, `year`, `modification_id`, `generation_number`, `restyling_number`, `wheel`, `frame`, `region_id` |
| `GET /rate-car/similar-cars` | `firm_id`, `model_id`, `year`, `modification_id`, `generation_number`, `restyling_number`, `wheel`, `frame`, `region_id` |

`wheel` accepts `UNDEFINED`, `LEFT`, `RIGHT`, or `LEFT_OR_RIGHT`. The models
endpoint also accepts `region_id`, `only_catalog`, and `with_special`;
frames accepts `with_special` and `with_other_frame`.

## Run with Docker Compose

```bash
docker compose up --build
```

The API is available at [http://localhost:8000/health](http://localhost:8000/health).
