# Cars Compare API

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --app-dir src --reload
```

The health endpoint is available at [http://localhost:8000/health](http://localhost:8000/health).
The rate-car API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Auction endpoints

| Endpoint | Required parameters |
| --- | --- |
| `GET /auctions` | `firm`, `model` |

`year` and `engine_volume` are optional filters:

```text
GET /auctions?firm=toyota&model=aqua&year=2020&engine_volume=1500
```

The response contains `query`, matching `examples`, and `avg_price` as an integer
average of all JPY prices available in the examples.

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
| `GET /rate-car/combined` | `firm_id`, `model_id`, `year`, `modification_id`, `generation_number`, `restyling_number`, `wheel`, `frame`, `region_id`, `import_purpose` |

`/rate-car/combined` returns `price_change_chart`, `similar_cars`, and
`auctions` together with `japan_import_response`. The auction filters are
derived from the firm, model, year, and engine displacement parsed from the
selected modification. `import_purpose` accepts `USAGE` or `RESALE`.
If no positive auction prices are available, `japan_import_response` is `null`;
the other combined results are still returned.

`wheel` accepts `UNDEFINED`, `LEFT`, `RIGHT`, or `LEFT_OR_RIGHT`. The models
endpoint also accepts `region_id`, `only_catalog`, and `with_special`;
frames accepts `with_special` and `with_other_frame`.
Catalog responses are cached in process memory for 24 hours.

## Run with Docker Compose

```bash
docker compose up --build
```

The API is available at [http://localhost:8000/health](http://localhost:8000/health).

## Run in development mode with Docker Compose

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

In development mode, `src` is mounted into the container and Uvicorn reloads the
API when Python files change. Stop the container with `Ctrl+C`.
