from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import regions_config
from app.parser.combined_compare import get_combined_compare
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
) -> CombinedCarRateResponse:
    try:
        return await get_combined_compare(query)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
