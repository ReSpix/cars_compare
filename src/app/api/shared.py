from math import ceil
from time import monotonic
from typing import Annotated

import aiohttp
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from app import regions_config
from app.parser.combined_compare import get_combined_compare
from app.parser.budget_alternatives import (
    AlternativesQuery,
    AlternativesResult,
    SourceUnavailable,
    retry_seconds,
    source_url,
)
from app.report_cache import ReportsBusy
from app.parser.budget_photos import PHOTO_ROUTE
from app.schemas import (
    CarCompareQuery,
    CombinedCarRateResponse,
    Region,
)

router = APIRouter()


@router.get("/regions", response_model=list[Region])
async def regions() -> list[Region]:
    return [Region.model_validate(region) for region in regions_config.REGIONS]


@router.get("/car_compare", response_model=CombinedCarRateResponse)
async def combined_car_rate(
    query: Annotated[CarCompareQuery, Query()],
    request: Request,
) -> CombinedCarRateResponse:
    async def load_report():
        remaining = request.app.state.comparison_retry_at - monotonic()
        if remaining > 0:
            raise SourceUnavailable(429, ceil(remaining))
        try:
            return await get_combined_compare(query)
        except aiohttp.ClientResponseError as error:
            if error.status != 429:
                raise
            seconds = retry_seconds((error.headers or {}).get("Retry-After"))
            request.app.state.comparison_retry_at = max(
                request.app.state.comparison_retry_at, monotonic() + seconds
            )
            raise SourceUnavailable(429, seconds) from error

    try:
        return await request.app.state.report_cache.get(
            "comparison-v2",
            query,
            CombinedCarRateResponse,
            load_report,
            timeout=65,
            cacheable=lambda report: not report.source_errors,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ReportsBusy as error:
        raise HTTPException(503, "Сейчас много запросов. Попробуйте через несколько секунд.") from error
    except TimeoutError as error:
        raise HTTPException(504, "Источники не успели ответить. Попробуйте пересчитать.") from error
    except SourceUnavailable as error:
        raise HTTPException(
            429,
            "Дром временно ограничил частоту запросов. Попробуйте позже.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except (aiohttp.ClientError, RuntimeError) as error:
        raise HTTPException(502, "Не удалось получить данные Дрома.") from error


@router.post("/budget-alternatives", response_model=AlternativesResult)
async def budget_alternatives(query: AlternativesQuery, request: Request) -> AlternativesResult:
    try:
        return await request.app.state.report_cache.get(
            "alternatives-v2",
            query,
            AlternativesResult,
            lambda: request.app.state.drom_alternatives.find(query),
            timeout=45,
        )
    except ReportsBusy as error:
        status, message, headers = 503, "Сейчас много запросов. Попробуйте позже.", None
        cause = error
    except TimeoutError as error:
        status, message, headers = 504, "Дром не успел ответить.", None
        cause = error
    except SourceUnavailable as error:
        cause = error
        if error.status == 429:
            status, message = 429, "Дром временно ограничил частоту запросов."
            headers = {"Retry-After": str(error.retry_after)}
        else:
            status, message, headers = 502, "Дром временно не вернул подборку с нужными фильтрами.", None
    raise HTTPException(status, {"message": message, "source_url": source_url(query)}, headers) from cause


@router.get(f"{PHOTO_ROUTE}/{{name}}", include_in_schema=False)
async def budget_photo(name: str, request: Request) -> Response:
    asset = request.app.state.budget_photos.get(name)
    if not asset:
        raise HTTPException(404, "Фото недоступно")
    content, media_type = asset
    return Response(content, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})
