import asyncio
import json
from contextlib import AsyncExitStack

import aiohttp
from bs4 import BeautifulSoup

from app.schemas import AuctionQuery, Car


async def parse_drom(
    url: str, session: aiohttp.ClientSession | None = None, *, strict: bool = False
) -> list[Car]:
    try:
        async with AsyncExitStack() as stack:
            if session is None:
                session = await stack.enter_async_context(aiohttp.ClientSession())

            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                page = await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        if strict:
            raise
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


async def parse_auction(
    url: str, session: aiohttp.ClientSession | None = None, *, strict: bool = False
) -> list[Car]:
    """Parse a Drom Japan auction listing."""
    return await parse_drom(url=url, session=session, strict=strict)


def get_url(query: AuctionQuery):
    url = f"https://www.drom.ru/world/japan/{query.firm}/{query.model}/"

    parameters = []

    if query.year is not None:
        parameters.append(f"yearFrom={query.year}")
        parameters.append(f"yearTo={query.year}")

    if query.engine_volume is not None:
        parameters.append(f"engineVolumeFrom={query.engine_volume}")
        parameters.append(f"engineVolumeTo={query.engine_volume}")

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
