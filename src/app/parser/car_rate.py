"""
Цепочка:
    firms → models → years → frames → generations → modifications → rate-car
"""

import asyncio
from typing import Any

import aiohttp

from app.schemas import (
    Firm,
    Generation,
    Model,
    Modification,
    PriceChangeChart,
    SimilarCars,
    Wheel,
)

# ────────────────────────────────────────────────────────────
# Конфигурация
# ────────────────────────────────────────────────────────────

GRAPHQL_URL = "https://graph.drom.ru/v1.0/sales"
RATE_BASE = "https://www.drom.ru/api/sales/rate-car"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS_GQL = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": "https://auto.drom.ru",
    "Referer": "https://auto.drom.ru/rate_car/",
    "User-Agent": _UA,
}

HEADERS_REST = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://auto.drom.ru/rate_car/",
    "User-Agent": _UA,
}

WHEEL_TO_INT: dict[Wheel, int] = {
    "UNDEFINED": 0,
    "LEFT": 1,
    "RIGHT": 2,
    "LEFT_OR_RIGHT": 3,
}
FRAME_TO_INT: dict[str, int] = {
    "other": 0,
    "OPEN": 1,
    "COUPE": 2,
    "SUV": 3,
    "HATCHBACK": 4,
    "SEDAN": 5,
    "MINIVAN_2_ROW_SEATS": 6,
    "VAN": 7,
    "WAGON": 8,
    "MINIVAN_3_ROW_SEATS": 9,
    "PICKUP": 10,
    "TRUCK": 11,
    "HATCHBACK_3DR": 12,
    "SUV_3DR": 13,
    "LIFTBACK": 14,
    "BUS": 15,
    "BOX_TRUCK": 16,
    "CHASSIS_CAB": 17,
    "TRUCK_TRACTOR": 18,
}


# ────────────────────────────────────────────────────────────
# Хелперы
# ────────────────────────────────────────────────────────────


async def _request_json(
    method: str,
    url: str,
    *,
    session: aiohttp.ClientSession | None = None,
    **kwargs: Any,
) -> dict:
    if session is None:
        async with aiohttp.ClientSession() as client:
            return await _request_json(method, url, session=client, **kwargs)

    async with session.request(
        method,
        url,
        timeout=aiohttp.ClientTimeout(total=20),
        **kwargs,
    ) as response:
        response.raise_for_status()
        return await response.json()


async def _gql(
    operation: str,
    variables: dict,
    query: str,
    session: aiohttp.ClientSession | None = None,
) -> dict:
    payload = {"operationName": operation, "variables": variables, "query": query}
    data = await _request_json(
        "POST", GRAPHQL_URL, headers=HEADERS_GQL, json=payload, session=session
    )
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data["data"]


async def _rest_get(
    endpoint: str,
    params: dict,
    session: aiohttp.ClientSession | None = None,
) -> dict:
    return await _request_json(
        "GET",
        f"{RATE_BASE}/{endpoint}/",
        headers=HEADERS_REST,
        params=params,
        session=session,
    )


def _dedup_by_id(items: list[dict]) -> list[dict]:
    seen, result = set(), []
    for it in items:
        if it["id"] not in seen:
            seen.add(it["id"])
            result.append(it)
    return result


# ────────────────────────────────────────────────────────────
# 1. Марки
# ────────────────────────────────────────────────────────────

_FIRMS_QUERY = """
query Firms {
  firms {
    topItems { id title }
    items    { id title }
  }
}
"""


async def get_firms_list(
    session: aiohttp.ClientSession | None = None,
) -> list[Firm]:
    data = await _gql("Firms", {}, _FIRMS_QUERY, session=session)
    f = data["firms"]
    return [Firm(**it) for it in _dedup_by_id(f["topItems"] + f["items"])]


# ────────────────────────────────────────────────────────────
# 2. Модели
# ────────────────────────────────────────────────────────────

_MODELS_QUERY = """
fragment modelFields on Model { id title wheels }

query Models($firm: PIntId!, $regionId: Int, $onlyCatalog: Boolean!, $withSpecial: Boolean!) {
  model: models(
    firmId: $firm
    topRegionId: $regionId
    onlyCatalog: $onlyCatalog
    withSpecialTrucks: $withSpecial
  ) {
    topItems { ...modelFields }
    items    { ...modelFields }
  }
}
"""


async def get_models_list(
    firm_id: int,
    region_id: int = 0,
    only_catalog: bool = True,
    with_special: bool = False,
    session: aiohttp.ClientSession | None = None,
) -> list[Model]:
    data = await _gql(
        "Models",
        {
            "firm": firm_id,
            "regionId": region_id,
            "onlyCatalog": only_catalog,
            "withSpecial": with_special,
        },
        _MODELS_QUERY,
        session=session,
    )
    m = data["model"]
    return [Model(**it) for it in _dedup_by_id(m["topItems"] + m["items"])]


# ────────────────────────────────────────────────────────────
# 3. Годы
# ────────────────────────────────────────────────────────────

_YEARS_QUERY = """
query Years($model: PIntId!, $wheel: Wheel) {
  year: years(modelId: $model, wheel: $wheel)
}
"""


async def get_years_list(
    model_id: int,
    wheel: Wheel,
    session: aiohttp.ClientSession | None = None,
) -> list[int]:
    data = await _gql(
        "Years", {"model": model_id, "wheel": wheel}, _YEARS_QUERY, session=session
    )
    return data["year"]


# ────────────────────────────────────────────────────────────
# 4. Кузова
# ────────────────────────────────────────────────────────────

_FRAMES_QUERY = """
query Frames($model: PIntId!, $wheel: Wheel, $year: Year,
             $withSpecial: Boolean!, $withOtherFrame: Boolean) {
  frame: frames(
    modelId: $model
    wheel: $wheel
    year: $year
    withSpecialTrucks: $withSpecial
    withOtherFrameCheck: $withOtherFrame
  )
}
"""


async def get_frames_list(
    model_id: int,
    year: int,
    wheel: Wheel,
    with_special: bool = False,
    with_other_frame: bool = False,
    session: aiohttp.ClientSession | None = None,
) -> list[str]:
    data = await _gql(
        "Frames",
        {
            "model": model_id,
            "wheel": wheel,
            "year": year,
            "withSpecial": with_special,
            "withOtherFrame": with_other_frame,
        },
        _FRAMES_QUERY,
        session=session,
    )
    return data["frame"]


# ────────────────────────────────────────────────────────────
# 5. Поколения
# ────────────────────────────────────────────────────────────

_GENERATIONS_QUERY = """
query Generations($model: PIntId!, $wheel: Wheel, $frame: CatalogFrame, $year: Year) {
  generation: generations(
    modelId: $model
    wheel: $wheel
    frame: $frame
    year: $year
  ) {
    id
    value
    title
    periodTitle
    generationNumber
    generationTitle
    restylingNumber
    restylingTitle
    frameTitle
  }
}
"""


async def get_generations_list(
    model_id: int,
    year: int,
    frame: str,
    wheel: Wheel,
    session: aiohttp.ClientSession | None = None,
) -> list[Generation]:
    data = await _gql(
        "Generations",
        {"model": model_id, "wheel": wheel, "frame": frame, "year": year},
        _GENERATIONS_QUERY,
        session=session,
    )
    return [Generation(**g) for g in data["generation"]]


# ────────────────────────────────────────────────────────────
# 6. Модификации
# ────────────────────────────────────────────────────────────

_MODIFICATIONS_QUERY = """
query Modifications($model: PIntId!, $frame: CatalogFrame, $wheel: Wheel,
                    $year: Year, $generation: String) {
  modification: modifications(
    modelId: $model
    frame: $frame
    wheel: $wheel
    year: $year
    generation: $generation
  ) {
    id
    title
  }
}
"""


async def get_modifications_list(
    model_id: int,
    year: int,
    frame: str,
    generation_value: str,
    wheel: Wheel,
    session: aiohttp.ClientSession | None = None,
) -> list[Modification]:
    data = await _gql(
        "Modifications",
        {
            "model": model_id,
            "wheel": wheel,
            "frame": frame,
            "year": year,
            "generation": generation_value,
        },
        _MODIFICATIONS_QUERY,
        session=session,
    )
    return [Modification(**m) for m in data["modification"]]


# ────────────────────────────────────────────────────────────
# 7. Финальные REST-вызовы
# ────────────────────────────────────────────────────────────


def _rate_params(
    firm_id: int,
    model_id: int,
    year: int,
    modification_id: int,
    generation_number: int,
    restyling_number: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
) -> dict:
    try:
        wheel_int = WHEEL_TO_INT[wheel]
    except KeyError:
        raise ValueError(f"Unknown wheel: {wheel!r}. Known: {list(WHEEL_TO_INT)}")
    try:
        frame_int = FRAME_TO_INT[frame]
    except KeyError:
        raise ValueError(f"Unknown frame: {frame!r}. Known: {list(FRAME_TO_INT)}")

    return {
        "regionId": region_id,
        "firm": firm_id,
        "model": model_id,
        "year": year,
        "modification": modification_id,
        "generationNumber": generation_number,
        "restylingNumber": restyling_number,
        "wheel": wheel_int,
        "frame": frame_int,
    }


async def get_price_change_chart(
    firm_id: int,
    model_id: int,
    year: int,
    modification_id: int,
    generation_number: int,
    restyling_number: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
    session: aiohttp.ClientSession | None = None,
) -> PriceChangeChart:
    raw = await _rest_get(
        "price-change-chart",
        _rate_params(
            firm_id,
            model_id,
            year,
            modification_id,
            generation_number,
            restyling_number,
            wheel,
            frame,
            region_id,
        ),
        session=session,
    )
    return PriceChangeChart(**raw)


async def get_similar_cars(
    firm_id: int,
    model_id: int,
    year: int,
    modification_id: int,
    generation_number: int,
    restyling_number: int,
    wheel: Wheel,
    frame: str,
    region_id: int,
    session: aiohttp.ClientSession | None = None,
) -> SimilarCars:
    raw = await _rest_get(
        "similar-cars",
        _rate_params(
            firm_id,
            model_id,
            year,
            modification_id,
            generation_number,
            restyling_number,
            wheel,
            frame,
            region_id,
        ),
        session=session,
    )
    return SimilarCars(**raw)


# ────────────────────────────────────────────────────────────
# Демонстрация
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":

    async def main() -> None:
        REGION_ID = 25
        WHEEL: Wheel = "LEFT"
        FRAME = "SEDAN"
        YEAR = 2020
        WITH_SPECIAL = False
        WITH_OTHER_FRAME = False
        ONLY_CATALOG = True

        async with aiohttp.ClientSession() as session:
            print("1) Марки…")
            firms = await get_firms_list(session)
            toyota = next(f for f in firms if f.title == "Toyota")
            print(f"   Toyota id={toyota.id}")

            print("2) Модели Toyota…")
            models = await get_models_list(
                toyota.id, 0, ONLY_CATALOG, WITH_SPECIAL, session
            )
            camry = next(m for m in models if m.title == "Camry")
            print(f"   Camry id={camry.id}  wheels={camry.wheels}")

            print("3) Годы Camry…")
            years = await get_years_list(camry.id, WHEEL, session)
            print(f"   {years[:6]}… всего {len(years)}")

            print("4) Кузова на 2020…")
            frames = await get_frames_list(
                camry.id, YEAR, WHEEL, WITH_SPECIAL, WITH_OTHER_FRAME, session
            )
            print(f"   {frames}")

            print("5) Поколения 2020 / SEDAN…")
            generations = await get_generations_list(
                camry.id, YEAR, FRAME, WHEEL, session
            )
            for g in generations:
                print(
                    f"   {g.value:>4}  gen={g.generationNumber} "
                    f"rest={g.restylingNumber}  {g.title}"
                )
            generation = generations[0]

            print("6) Модификации…")
            modifications = await get_modifications_list(
                camry.id, YEAR, FRAME, generation.value, WHEEL, session
            )
            for m in modifications:
                print(f"   {m.id}: {m.title}")
            modification = modifications[0]

            print(f"\n7) Финальные вызовы для: {modification.title}")
            price = await get_price_change_chart(
                firm_id=toyota.id,
                model_id=camry.id,
                year=YEAR,
                modification_id=modification.id,
                generation_number=generation.generationNumber,
                restyling_number=generation.restylingNumber,
                wheel=WHEEL,
                frame=FRAME,
                region_id=REGION_ID,
                session=session,
            )
            print(
                f"   recommendedPrice={price.recommendedPrice:,} ₽  "
                f"averageSaleDays={price.averageSaleDays}"
            )

            similar = await get_similar_cars(
                firm_id=toyota.id,
                model_id=camry.id,
                year=YEAR,
                modification_id=modification.id,
                generation_number=generation.generationNumber,
                restyling_number=generation.restylingNumber,
                wheel=WHEEL,
                frame=FRAME,
                region_id=REGION_ID,
                session=session,
            )
            print(f"   similar-cars: {len(similar.bulls)} объявлений")
            for b in similar.bulls[:5]:
                print(f"     {b.price:>10,} ₽  {b.url}")

    asyncio.run(main())
