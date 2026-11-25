import asyncio
import json
import re
from collections import OrderedDict
from time import monotonic
from urllib.parse import urlsplit

import aiohttp
from bs4 import BeautifulSoup, SoupStrainer

_MAX_LISTINGS = 8
_CONCURRENT_REQUESTS = 3
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=8)
_CACHE_MAX_SIZE = 512
_CACHE_TTL_SECONDS = 3600
_MISSING_TTL_SECONDS = 120

_cache: OrderedDict[str, tuple[float, int | None]] = OrderedDict()


def parse_listing_mileage(page: str, expected_url: str | None = None) -> int | None:
    """Прочитать пробег в километрах из JSON-LD самого объявления."""

    def objects(value):
        if isinstance(value, list):
            for item in value:
                yield from objects(item)
        elif isinstance(value, dict):
            yield value
            if "@graph" in value:
                yield from objects(value["@graph"])

    scripts = BeautifulSoup(
        page,
        "html.parser",
        parse_only=SoupStrainer("script", attrs={"type": "application/ld+json"}),
    )
    for script in scripts.find_all("script"):
        try:
            data = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue
        for car in objects(data):
            if car.get("@type") != "Car":
                continue
            offers = car.get("offers")
            offer_url = offers.get("url") if isinstance(offers, dict) else None
            source_url = car.get("url") or offer_url
            if (
                expected_url
                and source_url
                and source_url.rstrip("/") != expected_url.rstrip("/")
            ):
                continue
            odometer = car.get("mileageFromOdometer")
            if not isinstance(odometer, dict):
                continue
            if str(odometer.get("unitCode", "")).casefold() not in {"kmt", "km"}:
                continue
            value = re.sub(r"\s+", "", str(odometer.get("value", "")))
            if re.fullmatch(r"\d+", value):
                return int(value)
    return None


async def get_listing_mileage(url: str, session: aiohttp.ClientSession) -> int | None:
    try:
        target = urlsplit(url)
        if (
            target.scheme != "https"
            or target.hostname != "auto.drom.ru"
            or target.username
            or target.port not in (None, 443)
        ):
            return None
    except ValueError:
        return None
    cached = _cache.get(url)
    if cached and cached[0] > monotonic():
        _cache.move_to_end(url)
        return cached[1]
    mileage = None
    try:
        async with session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=False,
        ) as response:
            if response.status == 200:
                mileage = parse_listing_mileage(await response.text(), expected_url=url)
    except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeError):
        pass
    ttl = _CACHE_TTL_SECONDS if mileage is not None else _MISSING_TTL_SECONDS
    _cache[url] = (monotonic() + ttl, mileage)
    _cache.move_to_end(url)
    while len(_cache) > _CACHE_MAX_SIZE:
        _cache.popitem(last=False)
    return mileage


async def enrich_listing_mileages(
    bulls: list[dict], session: aiohttp.ClientSession | None = None
) -> list[dict]:
    if session is None:
        async with aiohttp.ClientSession() as client:
            return await enrich_listing_mileages(bulls, session=client)
    semaphore = asyncio.Semaphore(_CONCURRENT_REQUESTS)

    async def load(url):
        async with semaphore:
            return url, await get_listing_mileage(url, session)

    # Загружаем пробег только для показываемых карточек, чтобы не задерживать отчёт.
    urls = dict.fromkeys(bull["url"] for bull in bulls[:_MAX_LISTINGS])
    mileages = dict(await asyncio.gather(*(load(url) for url in urls)))
    return [{**bull, "mileage": mileages.get(bull["url"])} for bull in bulls]
