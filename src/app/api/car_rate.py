from fastapi import APIRouter, HTTPException

from app import regions_config
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
from app.parser.combined_compare import get_combined_compare
from app.schemas import (
    CombinedCarRateResponse,
    Firm,
    Generation,
    ImportPurpose,
    Model,
    Modification,
    PriceChangeChart,
    Region,
    SimilarCars,
    Wheel,
)

router = APIRouter(prefix="/rate-car", tags=["rate-car"])


@router.get("/regions", response_model=list[Region])
async def regions() -> list[Region]:
    return [Region.model_validate(region) for region in regions_config.REGIONS]


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
async def frames(
    model_id: int,
    year: int,
    wheel: Wheel,
    with_special: bool = False,
    with_other_frame: bool = False,
) -> list[str]:
    return await get_frames_list(
        model_id=model_id,
        year=year,
        wheel=wheel,
        with_special=with_special,
        with_other_frame=with_other_frame,
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
    generation_number: int,
    restyling_number: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
) -> PriceChangeChart:
    return await get_price_change_chart(
        firm_id=firm_id,
        model_id=model_id,
        year=year,
        modification_id=modification_id,
        generation_number=generation_number,
        restyling_number=restyling_number,
        wheel=wheel,
        frame=frame,
        region_id=region_id,
    )


@router.get("/similar-cars", response_model=SimilarCars)
async def similar_cars(
    firm_id: int,
    model_id: int,
    year: int,
    modification_id: int,
    generation_number: int,
    restyling_number: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
) -> SimilarCars:
    return await get_similar_cars(
        firm_id=firm_id,
        model_id=model_id,
        year=year,
        modification_id=modification_id,
        generation_number=generation_number,
        restyling_number=restyling_number,
        wheel=wheel,
        frame=frame,
        region_id=region_id,
    )


@router.get("/combined", response_model=CombinedCarRateResponse)
async def combined_car_rate(
    firm_id: int,
    model_id: int,
    year: int,
    modification_id: int,
    generation_number: int,
    restyling_number: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
    import_purpose: ImportPurpose,
) -> CombinedCarRateResponse:
    try:
        return await get_combined_compare(
            firm_id=firm_id,
            model_id=model_id,
            year=year,
            modification_id=modification_id,
            generation_number=generation_number,
            restyling_number=restyling_number,
            wheel=wheel,
            frame=frame,
            region_id=region_id,
            import_purpose=import_purpose,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
