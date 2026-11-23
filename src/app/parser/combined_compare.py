import asyncio
import re
from datetime import date
from decimal import Decimal

import aiohttp

from app.parser.auction import get_url, parse_auction
from app.parser.car_rate import (
    get_firms_list,
    get_generation_and_modification,
    get_models_list,
    get_price_change_chart,
    get_similar_cars,
)
from app.parser.japan_calculator import DromJapanCalculator
from app.schemas import (
    AuctionQuery,
    AuctionResponse,
    CarCompareQuery,
    CombinedCarRateResponse,
    CombinedResultsAvailability,
    Currency,
    EngineType,
    JapanImportRequest,
    ResultAvailability,
    VehicleAge,
)


def _auction_slug(title: str) -> str:
    return re.sub(r"\s+", "_", title.strip().lower())


def _engine_volume_from_modification(title: str) -> int | None:
    match = re.search(
        r"^\s*(\d+(?:[.,]\d+)?)\s*л(?:\.?)(?=\s*,)",
        title,
    )
    if match is None:
        return None
    return int(Decimal(match.group(1).replace(",", ".")) * 1000)


def _engine_horse_power_from_modification(title: str) -> int | None:
    match = re.search(r"(?<!\d)(\d+)\s*л\.?\s*с\.?(?!\w)", title, re.IGNORECASE)
    return int(match.group(1)) if match is not None else None


def _engine_type_from_modification(title: str) -> EngineType | None:
    normalized_title = title.casefold()
    if any(fuel in normalized_title for fuel in ("бензин", "дизел", "гибрид")):
        return EngineType.DIESEL_OR_GASOLINE
    if "электр" in normalized_title or "electric" in normalized_title:
        return EngineType.ELECTRIC_MOTOR
    return None


def _vehicle_age_from_year(year: int) -> VehicleAge:
    age = date.today().year - year
    if age < 3:
        return VehicleAge.UNDER_3
    if age <= 5:
        return VehicleAge.FROM_3_TO_5
    return VehicleAge.OVER_5


async def get_combined_compare(
    query: CarCompareQuery,
) -> CombinedCarRateResponse:
    firm_id = query.firm_id
    model_id = query.model_id
    year = query.year
    modification_id = query.modification_id
    wheel = query.wheel
    frame = query.frame
    region_id = query.region_id

    async with aiohttp.ClientSession() as session:
        firms = await get_firms_list(session)
        firm = next((item for item in firms if item.id == firm_id), None)
        if firm is None:
            raise LookupError(f"Firm {firm_id} not found")

        models = await get_models_list(firm_id=firm_id, session=session)
        model = next((item for item in models if item.id == model_id), None)
        if model is None:
            raise LookupError(f"Model {model_id} not found for firm {firm_id}")

        _, modification = await get_generation_and_modification(
            model_id=model_id,
            year=year,
            frame=frame,
            wheel=wheel,
            modification_id=modification_id,
            session=session,
        )

        auction_firm = _auction_slug(firm.title)
        auction_model = _auction_slug(model.title)
        engine_type = query.engine_type or _engine_type_from_modification(
            modification.title
        )
        is_electric = engine_type is EngineType.ELECTRIC_MOTOR
        engine_volume = None
        if not is_electric:
            engine_volume = query.engine_volume or _engine_volume_from_modification(
                modification.title
            )
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
        price = query.price or auction_response.avg_price_jpy
        engine_horse_power = query.engine_horse_power or (
            _engine_horse_power_from_modification(modification.title)
        )
        japan_missing_fields = []
        if price <= 0:
            japan_missing_fields.append("price")
        if not is_electric and (
            engine_volume is None or engine_volume <= 0
        ):
            japan_missing_fields.append("engine_volume")
        if engine_horse_power is None or engine_horse_power <= 0:
            japan_missing_fields.append("engine_horse_power")
        if engine_type is None:
            japan_missing_fields.append("engine_type")

        if (
            price > 0
            and engine_horse_power is not None
            and engine_horse_power > 0
            and engine_type is not None
            and (
                is_electric
                or (engine_volume is not None and engine_volume > 0)
            )
        ):
            japan_import_request = JapanImportRequest(
                price=price,
                currency=Currency.YEN,
                vehicleAge=_vehicle_age_from_year(year),
                engineType=engine_type,
                engineVolumeInCubicCentimeters=engine_volume,
                engineHorsePower=engine_horse_power,
                importPurpose=query.import_purpose,
            )
            japan_import_response = await DromJapanCalculator(session=session).calculate(
                japan_import_request
            )

        results_availability = CombinedResultsAvailability(
            price_change_chart=ResultAvailability(available=True),
            similar_cars=ResultAvailability(available=True),
            auctions=ResultAvailability(available=True),
            japan_import_response=ResultAvailability(
                available=japan_import_response is not None,
                missing_fields=japan_missing_fields,
            ),
        )

        return CombinedCarRateResponse(
            price_change_chart=price_change_task.result(),
            similar_cars=similar_cars_task.result(),
            auctions=auction_response,
            japan_import_response=japan_import_response,
            results_availability=results_availability,
        )
