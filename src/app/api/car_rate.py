from fastapi import APIRouter, HTTPException

from app.parser.car_rate import (
    get_firms_list,
    get_frames_list,
    get_generations_list,
    get_models_list,
    get_modifications_list,
    get_price_change_chart,
    get_similar_cars,
    get_years_list,
)
from app.schemas import (
    Firm,
    Generation,
    Model,
    Modification,
    PriceChangeChart,
    SimilarCars,
    Wheel,
)

router = APIRouter(prefix="/rate-car", tags=["rate-car"])


@router.get("/firms", response_model=list[Firm])
async def firms() -> list[Firm]:
    return await get_firms_list()


@router.get("/models", response_model=list[Model])
async def models(
    firm_id: int,
    region_id: int = 0,
    only_catalog: bool = True,
    with_special: bool = False,
) -> list[Model]:
    return await get_models_list(
        firm_id=firm_id,
        region_id=region_id,
        only_catalog=only_catalog,
        with_special=with_special,
    )


@router.get("/years", response_model=list[int])
async def years(model_id: int, wheel: Wheel) -> list[int]:
    return await get_years_list(model_id=model_id, wheel=wheel)


@router.get("/frames", response_model=list[str])
async def frames(model_id: int, year: int, wheel: Wheel) -> list[str]:
    return await get_frames_list(
        model_id=model_id,
        year=year,
        wheel=wheel,
        with_special=False,
        with_other_frame=False,
    )


@router.get("/generations", response_model=list[Generation])
async def generations(
    model_id: int,
    year: int,
    frame: str,
    wheel: Wheel,
) -> list[Generation]:
    return await get_generations_list(
        model_id=model_id,
        year=year,
        frame=frame,
        wheel=wheel,
    )


@router.get("/modifications", response_model=list[Modification])
async def modifications(
    model_id: int,
    year: int,
    frame: str,
    generation_id: str,
    wheel: Wheel,
) -> list[Modification]:
    available_generations = await get_generations_list(
        model_id=model_id,
        year=year,
        frame=frame,
        wheel=wheel,
    )
    generation = next(
        (item for item in available_generations if item.id == generation_id),
        None,
    )
    if generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")

    return await get_modifications_list(
        model_id=model_id,
        year=year,
        frame=frame,
        generation_value=generation.value,
        wheel=wheel,
    )


@router.get("/price-change-chart", response_model=PriceChangeChart)
async def price_change_chart(
    firm_id: int,
    model_id: int,
    year: int,
    modification_id: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
    generation_id: str | None = None,
) -> PriceChangeChart:
    try:
        return await get_price_change_chart(
            firm_id=firm_id,
            model_id=model_id,
            year=year,
            modification_id=modification_id,
            wheel=wheel,
            frame=frame,
            region_id=region_id,
            generation_id=generation_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/similar-cars", response_model=SimilarCars)
async def similar_cars(
    firm_id: int,
    model_id: int,
    year: int,
    modification_id: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
    generation_id: str | None = None,
) -> SimilarCars:
    try:
        return await get_similar_cars(
            firm_id=firm_id,
            model_id=model_id,
            year=year,
            modification_id=modification_id,
            wheel=wheel,
            frame=frame,
            region_id=region_id,
            generation_id=generation_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
