import asyncio
import json
import re
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Car(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str = Field(alias="name")
    year: int | None = Field(default=None, alias="productionDate")
    engine_volume: int | None = None
    mileage: int | None = None
    rating: float | None = None
    price_jpy: int | None = None
    url: str | None = None

    @field_validator("year", mode="before")
    @classmethod
    def parse_year(cls, value: Any) -> Any:
        if value is None:
            return None
        return int(value)

    @field_validator("engine_volume", "mileage", mode="before")
    @classmethod
    def parse_integer(cls, value: Any) -> int | None:
        if value is None:
            return None

        digits = re.sub(r"\D", "", str(value))
        return int(digits) if digits else None

    @field_validator("rating", mode="before")
    @classmethod
    def parse_rating(cls, value: Any) -> Any:
        return float(value) if value is not None else None

    @classmethod
    def from_json_ld(cls, data: dict) -> "Car":
        engine = data.get("vehicleEngine") or {}
        mileage = data.get("mileageFromOdometer") or {}
        rating = data.get("aggregateRating") or {}

        offers = data.get("offers") or []

        if isinstance(offers, dict):
            offers = [offers]

        jpy_offer = next(
            (offer for offer in offers if offer.get("priceCurrency") == "JPY"), None
        )

        return cls.model_validate(
            {
                "name": data.get("name"),
                "productionDate": data.get("productionDate"),
                "engine_volume": (engine.get("engineDisplacement")),
                "mileage": mileage.get("value"),
                "rating": rating.get("ratingValue"),
                "price_jpy": (jpy_offer.get("price") if jpy_offer else None),
                "url": data.get("url"),
            }
        )


async def parse_drom(
    url: str, session: aiohttp.ClientSession | None = None
) -> list[Car]:
    try:
        if session is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    page = await response.text()
        else:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                page = await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return []

    soup = BeautifulSoup(page, "html.parser")

    # Проверяем страницу 404 от Drom
    if soup.select_one('body[data-page-alias="404"]') or soup.find(
        "h1",
        string=lambda text: (
            text is not None and "Запрошенная вами страница не существует" in text
        ),
    ):
        return []

    cars = []

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue

        objects = data if isinstance(data, list) else [data]

        for item in objects:
            if not isinstance(item, dict):
                continue

            if item.get("@type") != "Car":
                continue

            try:
                cars.append(Car.from_json_ld(item))
            except (ValueError, TypeError):
                continue

    return cars


def get_url(
    firm: str, model: str, year: int | None = None, engine_volume: int | None = None
):
    url = f"https://www.drom.ru/world/japan/{firm}/{model}/"

    parameters = []

    if year is not None:
        parameters.append(f"yearFrom={year}")
        parameters.append(f"yearTo={year}")

    if engine_volume is not None:
        parameters.append(f"engineVolumeFrom={engine_volume}")
        parameters.append(f"engineVolumeTo={engine_volume}")

    if len(parameters) > 0:
        url += "?" + "&".join(parameters)

    return url


if __name__ == "__main__":
    async def main() -> None:
        url = get_url("toyota", "aqua", 2020, 1500)
        cars = await parse_drom(url)

        result = [car.model_dump() for car in cars]

        print(f"Найдено автомобилей: {len(cars)}")

        print(result)

    asyncio.run(main())
