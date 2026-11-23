import asyncio
import re
from datetime import date
from decimal import Decimal

import aiohttp

from app.parser.auction import get_url, parse_auction
from app.parser.car_rate import (
    get_firms_list,
    get_generations_list,
    get_models_list,
    get_modifications_list,
    get_price_change_chart,
    get_similar_cars,
)
from app.parser.japan_calculator import DromJapanCalculator
from app.schemas import (
    AuctionQuery,
    AuctionResponse,
    CombinedCarRateResponse,
    Currency,
    EngineType,
    ImportPurpose,
    JapanImportRequest,
    VehicleAge,
    Wheel,
)


def _auction_slug(title: str) -> str:
    return re.sub(r"\s+", "_", title.strip().lower())


def _engine_volume_from_modification(title: str) -> int | None:
    match = re.search(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*л(?:\.|(?=\s|,|$))", title)
    if match is None:
        return None
    return int(Decimal(match.group(1).replace(",", ".")) * 1000)


def _engine_horse_power_from_modification(title: str) -> int | None:
    match = re.search(r"(?<!\d)(\d+)\s*л\.?\s*с\.?(?!\w)", title, re.IGNORECASE)
    return int(match.group(1)) if match is not None else None


def _engine_type_from_modification(title: str) -> EngineType:
    normalized_title = title.casefold()
    if any(fuel in normalized_title for fuel in ("бензин", "дизел", "гибрид")):
        return EngineType.DIESEL_OR_GASOLINE
    if "электр" in normalized_title or "electric" in normalized_title:
        return EngineType.ELECTRIC_MOTOR
    raise ValueError("Cannot determine engine type from modification")


def _vehicle_age_from_year(year: int) -> VehicleAge:
    age = date.today().year - year
    if age < 3:
        return VehicleAge.UNDER_3
    if age <= 5:
        return VehicleAge.FROM_3_TO_5
    return VehicleAge.OVER_5


async def get_combined_compare(
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
    async with aiohttp.ClientSession() as session:
        firms = await get_firms_list(session)
        firm = next((item for item in firms if item.id == firm_id), None)
        if firm is None:
            raise LookupError(f"Firm {firm_id} not found")

        models = await get_models_list(firm_id=firm_id, session=session)
        model = next((item for item in models if item.id == model_id), None)
        if model is None:
            raise LookupError(f"Model {model_id} not found for firm {firm_id}")

        generations = await get_generations_list(
            model_id=model_id,
            year=year,
            frame=frame,
            wheel=wheel,
            session=session,
        )
        generation = next(
            (
                item
                for item in generations
                if item.generationNumber == generation_number
                and item.restylingNumber == restyling_number
            ),
            None,
        )
        if generation is None:
            raise LookupError("Generation not found")

        modifications = await get_modifications_list(
            model_id=model_id,
            year=year,
            frame=frame,
            generation_value=generation.value,
            wheel=wheel,
            session=session,
        )
        modification = next(
            (item for item in modifications if item.id == modification_id),
            None,
        )
        if modification is None:
            raise LookupError(f"Modification {modification_id} not found")

        auction_firm = _auction_slug(firm.title)
        auction_model = _auction_slug(model.title)
        engine_volume = _engine_volume_from_modification(modification.title)
        auction_query = AuctionQuery(
            firm=auction_firm,
            model=auction_model,
            year=year,
            engine_volume=engine_volume,
        )

        async with asyncio.TaskGroup() as tasks:
            price_change_task = tasks.create_task(
                get_price_change_chart(
                    firm_id=firm_id,
                    model_id=model_id,
                    year=year,
                    modification_id=modification_id,
                    generation_number=generation_number,
                    restyling_number=restyling_number,
                    wheel=wheel,
                    frame=frame,
                    region_id=region_id,
                    session=session,
                )
            )
            similar_cars_task = tasks.create_task(
                get_similar_cars(
                    firm_id=firm_id,
                    model_id=model_id,
                    year=year,
                    modification_id=modification_id,
                    generation_number=generation_number,
                    restyling_number=restyling_number,
                    wheel=wheel,
                    frame=frame,
                    region_id=region_id,
                    session=session,
                )
            )
            auction_examples_task = tasks.create_task(
                parse_auction(
                    get_url(
                        firm=auction_firm,
                        model=auction_model,
                        year=year,
                        engine_volume=engine_volume,
                    ),
                    session=session,
                )
            )

        auction_response = AuctionResponse(
            query=auction_query,
            examples=auction_examples_task.result(),
        )
        japan_import_response = None
        if auction_response.avg_price_jpy > 0:
            if engine_volume is None or engine_volume <= 0:
                raise ValueError("Cannot determine engine volume from modification")

            engine_horse_power = _engine_horse_power_from_modification(
                modification.title
            )
            if engine_horse_power is None or engine_horse_power <= 0:
                raise ValueError("Cannot determine engine horsepower from modification")

            japan_import_request = JapanImportRequest(
                price=auction_response.avg_price_jpy,
                currency=Currency.YEN,
                vehicleAge=_vehicle_age_from_year(year),
                engineType=_engine_type_from_modification(modification.title),
                engineVolumeInCubicCentimeters=engine_volume,
                engineHorsePower=engine_horse_power,
                importPurpose=import_purpose,
            )
            japan_import_response = await DromJapanCalculator(session=session).calculate(
                japan_import_request
            )

        return CombinedCarRateResponse(
            price_change_chart=price_change_task.result(),
            similar_cars=similar_cars_task.result(),
            auctions=auction_response,
            japan_import_response=japan_import_response,
        )
