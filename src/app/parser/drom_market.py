import asyncio
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import monotonic
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
from yarl import URL

DROM_HOST = "auto.drom.ru"
MARKET_CARD_LIMIT = 8
_PAGE_LIMIT = 2 * 1024 * 1024
_MARKET_PATH = re.compile(r"/(?:region\d+/)?[a-z0-9_-]+/[a-z0-9_-]+/(?:[a-z0-9_-]+/)*")
_LISTING_PATH = re.compile(r"/[a-z0-9_/-]+/(\d+)\.html")
_cooldown_until = 0.0


def drom_photo_url(value: str) -> str | None:
    try:
        url = urlsplit(value)
    except ValueError:
        return None
    if url.scheme == "https" and re.fullmatch(r"s\d*\.auto\.drom\.ru", url.netloc):
        return url.geturl()
    return None


def retry_seconds(value: str | None) -> int:
    try:
        return max(1, int(value))
    except (ValueError, TypeError):
        if value:
            try:
                retry_at = parsedate_to_datetime(value)
                return max(1, round((retry_at - datetime.now(UTC)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass
        return 60


def domestic_market_url(search_link: str, year: int) -> str | None:
    url = urlsplit(search_link)
    if url.scheme != "https" or url.netloc != DROM_HOST or not _MARKET_PATH.fullmatch(url.path):
        return None
    filters = {"minyear": year, "maxyear": year, "whereabouts[]": "0", "unsold": "1"}
    wheel = parse_qs(url.query).get("w", [])
    if wheel in (["1"], ["2"]):
        filters["w"] = wheel[0]
    return urlunsplit(("https", DROM_HOST, url.path, urlencode(filters), ""))


def listing_id(url: str) -> str | None:
    target = urlsplit(url)
    match = _LISTING_PATH.fullmatch(target.path)
    if target.scheme == "https" and target.netloc == DROM_HOST and match:
        return match[1]
    return None


def parse_market_cards(html: str, existing_ids: set[str], limit: int) -> list[dict]:
    if limit <= 0:
        return []
    soup = BeautifulSoup(html, "html.parser", parse_only=SoupStrainer(attrs={"data-ftid": "bulls-list_bull"}))
    cards = []
    seen = set(existing_ids)
    for card in soup.find_all(attrs={"data-ftid": "bulls-list_bull"}):
        links = [card] if card.has_attr("href") else card.find_all("a", href=True)
        listing_url = next((link["href"] for link in links if listing_id(link["href"])), None)
        price_node = card.find(attrs={"data-ftid": "bull_price"})
        if not listing_url or price_node is None:
            continue
        ident = listing_id(listing_url)
        price_match = re.search(r"\d[\d\s]*", price_node.get_text(" ", strip=True))
        if ident in seen or price_match is None:
            continue
        price = int(re.sub(r"\s", "", price_match[0]))
        if price <= 0:
            continue
        image = card.find("img", src=True)
        location = card.find(attrs={"data-ftid": "bull_location"})
        cards.append({
            "url": urlsplit(listing_url)._replace(query="", fragment="").geturl(),
            "price": price,
            "src": drom_photo_url(image["src"]) if image else None,
            "location": location.get_text(" ", strip=True) if location else None,
        })
        seen.add(ident)
        if len(cards) == limit:
            break
    return cards


async def get_market_cards(search_link: str, year: int, bulls: list[dict], session: aiohttp.ClientSession) -> list[dict]:
    global _cooldown_until
    limit = MARKET_CARD_LIMIT - len(bulls)
    if limit <= 0 or not search_link or _cooldown_until > monotonic():
        return []
    try:
        url = domestic_market_url(search_link, year)
        if not url:
            return []
        async with asyncio.timeout(5):
            for _ in range(2):
                async with session.get(url, allow_redirects=False) as response:
                    if response.status in {301, 302, 307, 308}:
                        target = response.url.join(URL(response.headers.get("Location", "")))
                        if target.scheme != "https" or target.raw_authority != DROM_HOST:
                            return []
                        url = str(target)
                        continue
                    if response.status == 429:
                        _cooldown_until = max(
                            _cooldown_until, monotonic() + retry_seconds(response.headers.get("Retry-After"))
                        )
                        return []
                    if response.status != 200:
                        return []
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        body.extend(chunk)
                        if len(body) > _PAGE_LIMIT:
                            return []
                    existing_ids = {ident for bull in bulls if (ident := listing_id(bull["url"]))}
                    return await asyncio.to_thread(
                        parse_market_cards, body.decode(response.charset or "utf-8", errors="replace"), existing_ids, limit
                    )
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, LookupError):
        pass
    return []
