import re
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Region(BaseModel):
    name: str
    code: int


class Car(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str = Field(alias="name")
    year: int | None = Field(default=None, alias="productionDate")
    engine_volume: int | None = None
    mileage: int | None = None
    rating: float | None = None
    price_jpy: int | None = None
    url: str | None = None
    image_url: str | None = None
    auction_date: date | None = None

    @field_validator("auction_date", mode="before")
    @classmethod
    def parse_auction_date(cls, value: Any) -> date | None:
        if value is None:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

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
    def from_json_ld(cls, data: dict[str, Any]) -> "Car":
        if not isinstance(data, dict):
            raise ValueError("Car JSON-LD must be an object")

        engine = data.get("vehicleEngine")
        engine = engine if isinstance(engine, dict) else {}
        mileage = data.get("mileageFromOdometer")
        mileage = mileage if isinstance(mileage, dict) else {}
        rating = data.get("aggregateRating")
        rating = rating if isinstance(rating, dict) else {}

        offers = data.get("offers") or []
        if isinstance(offers, dict):
            offers = [offers]
        elif not isinstance(offers, list):
            offers = []

        jpy_offer = next(
            (
                offer
                for offer in offers
                if isinstance(offer, dict) and offer.get("priceCurrency") == "JPY"
            ),
            None,
        )

        return cls.model_validate(
            {
                "name": data.get("name"),
                "productionDate": data.get("productionDate"),
                "engine_volume": engine.get("engineDisplacement"),
                "mileage": mileage.get("value"),
                "rating": rating.get("ratingValue"),
                "price_jpy": jpy_offer.get("price") if jpy_offer else None,
                "auction_date": jpy_offer.get("validFrom") if jpy_offer else None,
                "url": data.get("url"),
                "image_url": (data.get("image", {}).get("url", None)),
            }
        )


class AuctionQuery(BaseModel):
    firm: str = Field(min_length=1)
    model: str = Field(min_length=1)
    year: int | None = Field(default=None, ge=1900, le=2100)
    engine_volume: int | None = Field(default=None, ge=1)

    @field_validator("firm", "model")
    @classmethod
    def lowercase_name(cls, value: str) -> str:
        return value.lower()


class AuctionResponse(BaseModel):
    query: AuctionQuery
    url: str
    examples: list[Car]
    avg_price_jpy: int = 0
    priced_lot_count: int = 0
    dated_lot_count: int = 0
    period_start: date | None = None
    period_end: date | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    avg_mileage_km: int | None = None
    mileage_count: int = 0

    @model_validator(mode="after")
    def calculate_average_price(self) -> "AuctionResponse":
        priced_cars = [
            car
            for car in self.examples
            if car.price_jpy is not None and car.price_jpy > 0
        ]
        prices = [car.price_jpy for car in priced_cars]
        dates = [car.auction_date for car in priced_cars if car.auction_date]
        self.avg_price_jpy = sum(prices) // len(prices) if prices else 0
        self.priced_lot_count = len(prices)
        self.dated_lot_count = len(dates)
        self.period_start = min(dates) if dates else None
        self.period_end = max(dates) if dates else None
        mileages = [
            car.mileage
            for car in priced_cars
            if car.mileage is not None and car.mileage >= 0
        ]
        self.mileage_count = len(mileages)
        self.avg_mileage_km = round(sum(mileages) / len(mileages)) if mileages else None
        return self


Wheel = Literal["UNDEFINED", "LEFT", "RIGHT", "LEFT_OR_RIGHT"]


class DromCatalogModel(BaseModel):
    model_config = {"extra": "ignore"}


class Firm(DromCatalogModel):
    id: int
    title: str


class Model(DromCatalogModel):
    id: int
    title: str
    wheels: list[Wheel]


class Generation(DromCatalogModel):
    id: str
    value: str
    title: str
    periodTitle: str
    generationNumber: int
    generationTitle: str
    restylingNumber: int
    restylingTitle: str
    frameTitle: str


class Modification(DromCatalogModel):
    id: int
    title: str


class Bull(DromCatalogModel):
    url: str
    src: str | None = None
    src2x: str | None = None
    price: int
    mileage: int | None = Field(default=None, ge=0)


class PriceChangeChart(DromCatalogModel):
    recommendedPrice: int | None = None
    averageSaleDays: int | None = None
    unavailable_reason: Literal["insufficient_data", "source_unavailable"] | None = None


class SimilarCars(DromCatalogModel):
    bulls: list[Bull] = Field(default_factory=list)
    searchLink: str
    myCarAddToDraftLink: str | None = None
    avg_mileage_km: int | None = None
    mileage_count: int = 0

    @model_validator(mode="after")
    def calculate_average_mileage(self) -> "SimilarCars":
        mileages = [bull.mileage for bull in self.bulls if bull.mileage is not None]
        self.mileage_count = len(mileages)
        self.avg_mileage_km = round(sum(mileages) / len(mileages)) if mileages else None
        return self

    @field_validator("bulls", mode="before")
    @classmethod
    def validate_bulls(cls, v: Any) -> Any:
        return [] if v is None else v


class ResultAvailability(BaseModel):
    available: bool
    missing_fields: list[str] = Field(default_factory=list)


class CombinedResultsAvailability(BaseModel):
    price_change_chart: ResultAvailability
    similar_cars: ResultAvailability
    auctions: ResultAvailability
    japan_import_response: ResultAvailability


class Currency(str, Enum):
    YEN = "YEN"
    EUR = "EUR"
    USD = "USD"


class VehicleAge(str, Enum):
    UNDER_3 = "UNDER_3"
    FROM_3_TO_5 = "FROM_3_TO_5"
    OVER_5 = "OVER_5"


class EngineType(str, Enum):
    DIESEL_OR_GASOLINE = "DIESEL_OR_GASOLINE"
    ELECTRIC_MOTOR = "ELECTRIC_MOTOR"


class ImportPurpose(str, Enum):
    USAGE = "USAGE"
    RESALE = "RESALE"


class CarCompareQuery(BaseModel):
    firm_id: int = Field(description="Required input: firm catalog ID.")
    model_id: int = Field(description="Required input: model catalog ID.")
    year: int = Field(description="Required input: vehicle model year.")
    modification_id: int = Field(description="Required input: modification ID.")
    generation_id: str | None = Field(
        default=None, description="Selected catalog generation ID."
    )
    wheel: Wheel = Field(description="Required input: steering wheel position.")
    frame: str = Field(description="Required input: body type.")
    region_id: int = Field(description="Required input: Drom region ID.")
    import_purpose: ImportPurpose = Field(
        description="Required input: USAGE or RESALE."
    )
    price: int | None = Field(
        default=None,
        gt=0,
        json_schema_extra={"x-auto-extracted": True},
        description=(
            "Optional manual Japan import price in JPY. If omitted, the average "
            "auction price is used when available."
        ),
    )
    engine_volume: int | None = Field(
        default=None,
        gt=0,
        json_schema_extra={"x-auto-extracted": True},
        description=(
            "Optional manual engine volume in cubic centimeters. If omitted, "
            "the value is extracted from the selected modification."
        ),
    )
    engine_horse_power: int | None = Field(
        default=None,
        gt=0,
        json_schema_extra={"x-auto-extracted": True},
        description=(
            "Optional manual engine horsepower. If omitted, the value is "
            "extracted from the selected modification."
        ),
    )
    engine_type: EngineType | None = Field(
        default=None,
        json_schema_extra={"x-auto-extracted": True},
        description=(
            "Optional manual engine type. If omitted, the value is extracted "
            "from the selected modification."
        ),
    )


class DromJapanModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class JapanImportRequest(DromJapanModel):
    price: int = Field(gt=0, description="Price in JPY")
    currency: Currency
    vehicle_age: VehicleAge = Field(alias="vehicleAge")
    engine_type: EngineType = Field(alias="engineType")
    engine_volume: int | None = Field(
        default=None,
        alias="engineVolumeInCubicCentimeters",
        gt=0,
    )
    engine_horse_power: int = Field(alias="engineHorsePower", gt=0)
    import_purpose: ImportPurpose = Field(alias="importPurpose")

    def to_params(self) -> dict[str, str]:
        data = self.model_dump(by_alias=True, mode="json", exclude_none=True)
        return {key: str(value) for key, value in data.items()}


class Money(DromJapanModel):
    currency: str
    value: Decimal


class MoneyRange(DromJapanModel):
    left: Money
    right: Money


class CurrencyRate(DromJapanModel):
    currency: str
    value: Decimal
    multiplied_by: int | None = Field(default=None, alias="multipliedBy")


class CentralBankCurrencyRate(DromJapanModel):
    date: str
    form: dict[str, CurrencyRate]


class JapanForm(DromJapanModel):
    price: str
    currency: Currency
    vehicle_age: VehicleAge = Field(alias="vehicleAge")
    engine_type: EngineType = Field(alias="engineType")
    engine_volume: str | None = Field(
        default=None,
        alias="engineVolumeInCubicCentimeters",
    )
    engine_horse_power: str = Field(alias="engineHorsePower")
    import_purpose: ImportPurpose = Field(alias="importPurpose")


class PriceComponent(DromJapanModel):
    alt: Money | None = None
    major: Money | MoneyRange | None = None


class JapanCalculationDetails(DromJapanModel):
    PRICE: PriceComponent | None = None
    SPENDING_ABROAD: PriceComponent | None = None
    FREIGHT_TO_VLADIVOSTOK: PriceComponent | None = None
    SPENDING_TO_VLADIVOSTOK: PriceComponent | None = None
    REGISTRATION_COSTS: PriceComponent | None = None
    COMPANY_COMMISSION: PriceComponent | None = None
    CUSTOMS_DUTY: PriceComponent | None = None
    EXCISE_TAX: PriceComponent | None = None
    CUSTOMS_FEE: PriceComponent | None = None
    RECYCLING_FEE: PriceComponent | None = None
    VAT: PriceComponent | None = None
    SPENDING_AND_REGISTRATION: PriceComponent | None = None
    CUSTOMS_DUTY_AND_FEES: PriceComponent | None = None


class JapanCalculationResult(DromJapanModel):
    total_price: Money = Field(alias="totalPrice")
    details: JapanCalculationDetails


class JapanImportResponse(DromJapanModel):
    currency_rate: Any | None = Field(default=None, alias="currencyRate")
    central_bank_currency_rate: CentralBankCurrencyRate | None = Field(
        default=None,
        alias="centralBankCurrencyRate",
    )
    form: JapanForm
    result: JapanCalculationResult
    calculator_api: str = Field(alias="calculatorApi")
    currency_options: list[Currency] = Field(alias="currencyOptions")
    import_country: str = Field(alias="importCountry")


class CombinedCarRateResponse(BaseModel):
    query: CarCompareQuery
    price_change_chart: PriceChangeChart
    similar_cars: SimilarCars
    auctions: AuctionResponse
    japan_import_response: JapanImportResponse | None = None
    results_availability: CombinedResultsAvailability
