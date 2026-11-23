import re
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
            (offer for offer in offers if offer.get("priceCurrency") == "JPY"),
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
                "url": data.get("url"),
            }
        )


class AuctionQuery(BaseModel):
    firm: str = Field(min_length=1)
    model: str = Field(min_length=1)
    year: int | None = Field(default=None, ge=1900, le=2100)
    engine_volume: int | None = Field(default=None, ge=1)


class AuctionResponse(BaseModel):
    query: AuctionQuery
    examples: list[Car]
    avg_price_jpy: int = 0

    @model_validator(mode="after")
    def calculate_average_price(self) -> "AuctionResponse":
        prices = [
            car.price_jpy
            for car in self.examples
            if car.price_jpy is not None and car.price_jpy > 0
        ]
        self.avg_price_jpy = sum(prices) // len(prices) if prices else 0
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


class PriceChangeChart(DromCatalogModel):
    recommendedPrice: int
    averageSaleDays: int


class SimilarCars(DromCatalogModel):
    bulls: list[Bull]
    searchLink: str
    myCarAddToDraftLink: str | None = None

    @field_validator("bulls", mode="before")
    @classmethod
    def validate_bulls(cls, v: Any) -> Any:
        return [] if v is None else v


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


class DromJapanModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class JapanImportRequest(DromJapanModel):
    price: int = Field(gt=0)
    currency: Currency
    vehicle_age: VehicleAge = Field(alias="vehicleAge")
    engine_type: EngineType = Field(alias="engineType")
    engine_volume: int = Field(alias="engineVolumeInCubicCentimeters", gt=0)
    engine_horse_power: int = Field(alias="engineHorsePower", gt=0)
    import_purpose: ImportPurpose = Field(alias="importPurpose")

    def to_params(self) -> dict[str, str]:
        data = self.model_dump(by_alias=True, mode="json")
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
    engine_volume: str = Field(alias="engineVolumeInCubicCentimeters")
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
    price_change_chart: PriceChangeChart
    similar_cars: SimilarCars
    auctions: AuctionResponse
    japan_import_response: JapanImportResponse | None = None
