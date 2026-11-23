# Cars Compare API

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --app-dir src --reload
```

The health endpoint is available at [http://localhost:8000/health](http://localhost:8000/health).
The rate-car API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Log endpoint

`POST /log` accepts a plain-text string and stores it in the local SQLite
database. The default database is in memory; Docker sets
`LOG_DATABASE_PATH=/app/data/logs.db` to store logs in a file backed by the
`logs_data` Docker volume. Set `LOG_DATABASE_PATH` to a file path to use a file
database outside Docker.

```bash
curl -X POST http://localhost:8000/log \
  -H "Content-Type: text/plain" \
  --data "Example log message"
```

The response contains the ID of the stored log entry.

## Auction endpoints

| Endpoint | Required parameters |
| --- | --- |
| `GET /auctions` | `firm`, `model` |

`year` and `engine_volume` are optional filters:

```text
GET /auctions?firm=toyota&model=aqua&year=2020&engine_volume=1500
```

The response contains `query`, the fully populated auction search `url`,
matching `examples`, and `avg_price_jpy` as an integer average of all JPY
prices available in the examples.

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
| `GET /rate-car/price-change-chart` | `firm_id`, `model_id`, `year`, `modification_id`, `wheel`, `frame`, `region_id` |
| `GET /rate-car/similar-cars` | `firm_id`, `model_id`, `year`, `modification_id`, `wheel`, `frame`, `region_id` |
| `GET /rate-car/combined` | See the `CarCompareQuery` parameters in OpenAPI |

`/rate-car/combined` returns `price_change_chart`, `similar_cars`, and
`auctions` together with `japan_import_response`. The auction filters are
derived from the firm, model, year, and engine displacement parsed from the
selected modification. `import_purpose` accepts `USAGE` or `RESALE`.
If no positive auction prices are available, `japan_import_response` is `null`;
the other combined results are still returned. `query` contains the effective
query values, including automatically extracted `price`, `engine_volume`,
`engine_horse_power`, and `engine_type`; the frontend can detect or override
incorrectly extracted values in a follow-up request. `results_availability` reports
whether each combined result was obtained and lists the missing Japan calculator
fields (for example, `price`, `engine_volume`, `engine_horse_power`, or
`engine_type`) when it was not. Each entry contains `available` and
`missing_fields`; fields for manual completion use the Japan calculator's
snake_case input names. The required query fields identify the car and import
purpose. Optional `price`, `engine_volume`, `engine_horse_power`, and
`engine_type` parameters override values that the backend otherwise attempts
to derive automatically. Generation and restyling numbers for the combined,
price-change-chart, and similar-cars endpoints are resolved from
`modification_id` and do not need to be sent.
Electric vehicle modifications are identified by `электричество`;
`engine_volume` is not parsed or sent to Japan calculator for those vehicles.

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
