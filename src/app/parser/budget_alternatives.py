import asyncio
import json
import re
from datetime import UTC, datetime
from time import monotonic
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlsplit

import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
from pydantic import BaseModel, Field, model_validator
from yarl import URL

from app.parser.budget_photos import BudgetPhotoCache
from app.parser.drom_market import DROM_HOST, drom_photo_url, retry_seconds


# Коды кузовов в фильтре объявлений отличаются от кодов API оценки.
FRAME_CODES = {
    "OPEN": 11, "COUPE": 1, "SUV": 7, "HATCHBACK": 5, "SEDAN": 10,
    "MINIVAN_2_ROW_SEATS": 6, "MINIVAN_3_ROW_SEATS": 6, "WAGON": 3,
    "PICKUP": 12, "HATCHBACK_3DR": 4, "SUV_3DR": 8, "LIFTBACK": 9,
}
MAXIMUM_PAGE_BYTES = 3 * 1024 * 1024


class AlternativesQuery(BaseModel):
    budget_min: int = Field(default=0, ge=0)
    budget_max: int = Field(gt=0, le=9_007_199_254_740_991)
    year_from: int = Field(ge=1900, le=2099)
    year_to: int = Field(ge=1900, le=2099)
    frame: str = Field(min_length=1, max_length=32)
    model_id: int = Field(gt=0)

    @model_validator(mode="after")
    def check_ranges(self):
        if self.budget_min > self.budget_max or self.year_from > self.year_to:
            raise ValueError("Начало диапазона должно быть не больше конца.")
        return self


class Alternative(BaseModel):
    model_id: int = Field(gt=0)
    firm_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=150)
    price_from: int = Field(gt=0)
    price_to: int = Field(gt=0)
    year_from: int = Field(ge=1900, le=2099)
    year_to: int = Field(ge=1900, le=2099)
    count: int = Field(gt=0)
    features: str
    photo: str | None
    photo_candidates: list[str] = Field(default_factory=list, exclude=True)
    url: str


class AlternativesResult(BaseModel):
    status: Literal["ok", "empty", "unsupported_frame"]
    items: list[Alternative]
    source_url: str
    fetched_at: datetime


class SourceUnavailable(Exception):
    def __init__(self, status: int = 502, retry_after: int | None = None):
        self.status = status
        self.retry_after = retry_after


def _filter_params(query: AlternativesQuery, *, grouping: bool) -> list[tuple[str, str]]:
    params = [
        ("whereabouts[]", "2"),
        ("minyear", str(query.year_from)),
        ("maxyear", str(query.year_to)),
    ]
    if query.frame in FRAME_CODES:
        params.append(("frametype[]", str(FRAME_CODES[query.frame])))
    if grouping:
        params.append(("grouping", "1"))
    return params


def source_url(query: AlternativesQuery, model_path: str = "") -> str:
    filters = urlencode(_filter_params(query, grouping=not model_path))
    return f"https://{DROM_HOST}/{model_path}do-{query.budget_max}/?{filters}"


def _source_state(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser", parse_only=SoupStrainer("script"))
    for script in soup.find_all("script"):
        raw = script.string or ""
        if not raw.lstrip().startswith("{") or '"groupingSearchData"' not in raw and '"emptySearchResult"' not in raw:
            continue
        try:
            state = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(state, dict) and state.get("__slug") == "bulls-list-models-range":
            return state
    raise SourceUnavailable()


def _filter_applied(state: dict, query: AlternativesQuery) -> bool:
    filters = (state.get("filter") or {}).get("filledParams") or {}
    frames = filters.get("frameTypes") or []
    if not isinstance(frames, list):
        frames = [frames]
    return (
        str(filters.get("maxPrice")) == str(query.budget_max)
        and str(filters.get("minYear")) == str(query.year_from)
        and str(filters.get("maxYear")) == str(query.year_to)
        and {str(frame) for frame in frames} == {str(FRAME_CODES[query.frame])}
    )


def _model_path(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != DROM_HOST:
        return None
    if parse_qs(parsed.query).get("whereabouts[]") != ["2"]:
        return None
    match = re.match(r"^/([a-z0-9_-]+/[a-z0-9_-]+/)", parsed.path)
    return match[1] if match else None


def parse_alternatives(html: str, query: AlternativesQuery) -> list[Alternative]:
    state = _source_state(html)
    if not _filter_applied(state, query):
        raise SourceUnavailable()
    models = (state.get("modelRangeData") or {}).get("groupingSearchData")
    if models is None and state.get("emptySearchResult") is not None:
        return []
    if not isinstance(models, list):
        raise SourceUnavailable()

    matches: dict[tuple[int, int], Alternative] = {}
    valid_groups = 0
    for group in models:
        try:
            model_path = _model_path(group["bullListUrl"])
            ids = group["additionalSearchParams"]
            photos = list(dict.fromkeys(
                url for preview in group.get("previews") or []
                if isinstance(preview, dict) and (url := drom_photo_url(preview.get("photoUrl") or ""))
            ))
            card = Alternative(
                model_id=ids["modelId"],
                firm_id=ids["firmId"],
                title=group["groupTitle"],
                price_from=group["minPrice"],
                price_to=group["maxPrice"],
                year_from=group["minYear"],
                year_to=group["maxYear"],
                count=group["bullsCount"],
                features=group.get("facetDescription") or "",
                photo=None,
                photo_candidates=photos,
                url=source_url(query, model_path or ""),
            )
            frame_code = group.get("frameType")
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if not model_path:
            continue
        valid_groups += 1
        if (
            card.model_id != query.model_id
            and frame_code in (None, FRAME_CODES[query.frame], str(FRAME_CODES[query.frame]))
            and card.price_from <= card.price_to <= query.budget_max
            and query.year_from <= card.year_from <= card.year_to <= query.year_to
        ):
            matches.setdefault((card.firm_id, card.model_id), card)
    if models and not valid_groups:
        raise SourceUnavailable()
    return sorted(
        matches.values(),
        key=lambda card: (card.price_to < query.budget_min, -card.count),
    )[:6]


class DromAlternatives:
    def __init__(self, photos: BudgetPhotoCache | None = None):
        self.cooldown_until = 0.0
        self.photos = photos

    async def _fetch_page(self, url: str) -> str:
        headers = {"Accept": "text/html", "User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession(headers=headers) as session:
            for attempt in range(2):
                async with session.get(url, allow_redirects=False) as response:
                    if response.status == 429:
                        seconds = retry_seconds(response.headers.get("Retry-After"))
                        self.cooldown_until = max(self.cooldown_until, monotonic() + seconds)
                        raise SourceUnavailable(429, seconds)
                    if response.status in {301, 302, 307, 308} and attempt == 0:
                        redirect = response.url.join(URL(response.headers.get("Location", "")))
                        if redirect.scheme != "https" or redirect.raw_authority != DROM_HOST:
                            raise SourceUnavailable()
                        url = str(redirect)
                        continue
                    if response.status != 200:
                        raise SourceUnavailable(response.status)
                    page = bytearray()
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        page.extend(chunk)
                        if len(page) > MAXIMUM_PAGE_BYTES:
                            raise SourceUnavailable()
                    charset = response.charset
                    if charset:
                        return page.decode(charset)
                    try:
                        return page.decode("utf-8")
                    except UnicodeDecodeError:
                        return page.decode("windows-1251")
        raise SourceUnavailable()

    async def find(self, query: AlternativesQuery) -> AlternativesResult:
        url = source_url(query)
        if query.frame not in FRAME_CODES:
            return AlternativesResult(
                status="unsupported_frame", items=[], source_url=url, fetched_at=datetime.now(UTC)
            )
        remaining = self.cooldown_until - monotonic()
        if remaining > 0:
            raise SourceUnavailable(429, max(1, round(remaining)))
        try:
            async with asyncio.timeout(40):
                html = await self._fetch_page(url)
            items = await asyncio.to_thread(parse_alternatives, html, query)
        except (aiohttp.ClientError, ValueError, LookupError):
            raise SourceUnavailable() from None
        if self.photos and items:
            images = await self.photos.copy_all([item.photo_candidates for item in items])
            for item, image in zip(items, images):
                item.photo = image
        return AlternativesResult(
            status="ok" if items else "empty",
            items=items,
            source_url=url,
            fetched_at=datetime.now(UTC),
        )
