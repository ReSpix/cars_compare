import asyncio
import re
from hashlib import sha256
from pathlib import Path
from time import time

import aiohttp

from app.parser.drom_market import drom_photo_url

PHOTO_ROUTE = "/budget-alternatives/photos"
_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/png": "png",
    "image/avif": "avif",
}
_MIME_TYPES = {extension: mime for mime, extension in _EXTENSIONS.items()}
_NAME = re.compile(r"[0-9a-f]{64}\.(jpg|webp|png|avif)")
_TTL = 24 * 60 * 60
_MAX_FILES = 256
_MAX_BYTES = 512 * 1024


class BudgetPhotoCache:
    def __init__(self, directory: Path):
        self.directory = directory

    def get(self, name: str) -> tuple[bytes, str] | None:
        match = _NAME.fullmatch(name)
        if not match:
            return None
        path = self.directory / name
        try:
            if time() - path.stat().st_mtime <= _TTL:
                return path.read_bytes(), _MIME_TYPES[match[1]]
        except OSError:
            pass
        return None

    def _prune(self):
        expiry = time() - _TTL
        files = []
        for path in self.directory.iterdir():
            if _NAME.fullmatch(path.name):
                try:
                    written = path.stat().st_mtime
                    if written < expiry:
                        path.unlink(missing_ok=True)
                    else:
                        files.append((written, path))
                except OSError:
                    continue
        for _, path in sorted(files, reverse=True)[_MAX_FILES:]:
            path.unlink(missing_ok=True)

    def _save(self, path: Path, content: bytes):
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(path)

    async def _copy(self, urls: list[str], session: aiohttp.ClientSession) -> str | None:
        for candidate in urls[:2]:
            url = drom_photo_url(candidate)
            if not url:
                continue
            ident = sha256(url.encode()).hexdigest()
            try:
                for path in self.directory.glob(f"{ident}.*"):
                    if _NAME.fullmatch(path.name) and time() - path.stat().st_mtime <= _TTL:
                        return f"{PHOTO_ROUTE}/{path.name}"
                async with session.get(url, allow_redirects=False) as response:
                    extension = _EXTENSIONS.get(response.content_type)
                    if response.status != 200 or not extension:
                        continue
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        body.extend(chunk)
                        if len(body) > _MAX_BYTES:
                            break
                    if not body or len(body) > _MAX_BYTES:
                        continue
                    path = self.directory / f"{ident}.{extension}"
                    self._save(path, body)
                    return f"{PHOTO_ROUTE}/{path.name}"
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
                continue
        return None

    async def copy_all(self, candidates: list[list[str]]) -> list[str | None]:
        results = [None] * len(candidates)
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=3),
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://auto.drom.ru/"},
            timeout=aiohttp.ClientTimeout(total=2.5),
        ) as session:
            async def copy(index, urls):
                results[index] = await self._copy(urls, session)

            try:
                async with asyncio.timeout(3.5):
                    await asyncio.gather(*(copy(index, urls) for index, urls in enumerate(candidates) if urls))
            except TimeoutError:
                pass
        if any(results):
            try:
                self._prune()
            except OSError:
                pass
        return results
