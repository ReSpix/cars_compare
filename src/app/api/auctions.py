from fastapi import APIRouter, Query

from app.parser.auction import get_url, parse_auction
from app.schemas import AuctionQuery, AuctionResponse

router = APIRouter(prefix="/auctions", tags=["auctions"])


@router.get(
    "",
    response_model=AuctionResponse,
    summary="Get Drom Japan auction listings",
)
async def get_auctions(
    firm: str = Query(..., min_length=1),
    model: str = Query(..., min_length=1),
    year: int | None = Query(default=None, ge=1900, le=2100),
    engine_volume: int | None = Query(default=None, ge=1),
) -> AuctionResponse:
    query = AuctionQuery(
        firm=firm,
        model=model,
        year=year,
        engine_volume=engine_volume,
    )
    url = get_url(
        firm=firm,
        model=model,
        year=year,
        engine_volume=engine_volume,
    )
    examples = await parse_auction(url)
    return AuctionResponse(query=query, url=url, examples=examples)