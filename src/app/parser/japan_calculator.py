from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from enum import Enum
from typing import Any

import aiohttp
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# ============================================================
# CONFIG
# ============================================================

API_URL = "https://www.drom.ru/api/world/calculate/japan/"

DEFAULT_TIMEOUT = 20


# ============================================================
# ENUMS
# ============================================================


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


# ============================================================
# BASE MODEL
# ============================================================


class DromModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


# ============================================================
# REQUEST
# ============================================================


class JapanImportRequest(DromModel):
    price: int = Field(gt=0)

    currency: Currency

    vehicle_age: VehicleAge = Field(alias="vehicleAge")

    engine_type: EngineType = Field(alias="engineType")

    engine_volume: int = Field(
        alias="engineVolumeInCubicCentimeters",
        gt=0,
    )

    engine_horse_power: int = Field(
        alias="engineHorsePower",
        gt=0,
    )

    import_purpose: ImportPurpose = Field(alias="importPurpose")

    def to_params(self) -> dict[str, str]:
        """Преобразует модель в GET-параметры API."""
        data = self.model_dump(
            by_alias=True,
            mode="json",
        )

        return {key: str(value) for key, value in data.items()}


# ============================================================
# COMMON RESPONSE MODELS
# ============================================================


class Money(DromModel):
    currency: str
    value: Decimal


class MoneyRange(DromModel):
    left: Money
    right: Money


class CurrencyRate(DromModel):
    currency: str
    value: Decimal
    multiplied_by: int | None = Field(
        default=None,
        alias="multipliedBy",
    )


class CentralBankCurrencyRate(DromModel):
    date: str
    form: dict[str, CurrencyRate]


class JapanForm(DromModel):
    price: str
    currency: Currency
    vehicle_age: VehicleAge = Field(alias="vehicleAge")
    engine_type: EngineType = Field(alias="engineType")

    engine_volume: str = Field(alias="engineVolumeInCubicCentimeters")

    engine_horse_power: str = Field(alias="engineHorsePower")

    import_purpose: ImportPurpose = Field(alias="importPurpose")


# ============================================================
# CALCULATION DETAILS
# ============================================================


class PriceComponent(DromModel):
    """
    Одна статья расходов.

    alt   — сумма в альтернативной валюте.
    major — сумма в основной валюте либо диапазон.
    """

    alt: Money | None = None
    major: Money | MoneyRange | None = None


class JapanCalculationDetails(DromModel):
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


# ============================================================
# RESULT
# ============================================================


class JapanCalculationResult(DromModel):
    total_price: Money = Field(alias="totalPrice")
    details: JapanCalculationDetails


# ============================================================
# FULL RESPONSE
# ============================================================


class JapanImportResponse(DromModel):
    currency_rate: Any | None = Field(
        default=None,
        alias="currencyRate",
    )

    central_bank_currency_rate: CentralBankCurrencyRate | None = Field(
        default=None,
        alias="centralBankCurrencyRate",
    )

    form: JapanForm

    result: JapanCalculationResult

    calculator_api: str = Field(alias="calculatorApi")

    currency_options: list[Currency] = Field(alias="currencyOptions")

    import_country: str = Field(alias="importCountry")


# ============================================================
# API CLIENT
# ============================================================


class DromJapanCalculator:
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ):
        self.timeout = timeout
        self.session = session
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.drom.ru/",
        }

        if self.session is not None:
            self.session.headers.update(self.headers)

    async def calculate(
        self,
        request: JapanImportRequest,
    ) -> JapanImportResponse:
        """
        Выполняет расчёт стоимости автомобиля из Японии.

        :param request: параметры расчёта
        :return: типизированный ответ API
        """
        session = self.session
        owns_session = session is None
        if session is None:
            session = aiohttp.ClientSession(headers=self.headers)

        try:
            async with session.get(
                API_URL,
                params=request.to_params(),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                response.raise_for_status()

                try:
                    data = await response.json()
                except (json.JSONDecodeError, aiohttp.ContentTypeError) as exc:
                    body = await response.text()
                    raise RuntimeError(f"Drom вернул не JSON: {body[:500]}") from exc

            try:
                return JapanImportResponse.model_validate(data)
            except ValidationError as exc:
                raise RuntimeError(f"Не удалось разобрать ответ Drom API:\n{exc}") from exc
        finally:
            if owns_session:
                await session.close()


# ============================================================
# EXAMPLE
# ============================================================

if __name__ == "__main__":
    async def main() -> None:
        calculator = DromJapanCalculator()

        request = JapanImportRequest(
            price=1_000_000,
            currency=Currency.YEN,
            vehicleAge=VehicleAge.FROM_3_TO_5,
            engineType=EngineType.DIESEL_OR_GASOLINE,
            engineVolumeInCubicCentimeters=1500,
            engineHorsePower=100,
            importPurpose=ImportPurpose.USAGE,
        )

        result = await calculator.calculate(request)

        # Итоговая стоимость
        print("\nИТОГО:")
        print(
            result.result.total_price.currency,
            result.result.total_price.value,
        )

        # Курс валют ЦБ
        print("\nКУРСЫ ЦБ:")
        if result.central_bank_currency_rate:
            print("Дата:", result.central_bank_currency_rate.date)

            for currency, rate in result.central_bank_currency_rate.form.items():
                print(
                    currency,
                    rate.value,
                    rate.currency,
                    f"(за {rate.multiplied_by})" if rate.multiplied_by else "",
                )

        # Все статьи расходов
        print("\nДЕТАЛИЗАЦИЯ:")

        for name, component in result.result.details:
            if component is None:
                continue

            print(f"\n{name}:")

            if component.alt:
                print(
                    "  Альтернативная валюта:",
                    component.alt.currency,
                    component.alt.value,
                )

            if isinstance(component.major, Money):
                print(
                    "  Основная сумма:",
                    component.major.currency,
                    component.major.value,
                )

            elif isinstance(component.major, MoneyRange):
                print(
                    "  Диапазон:",
                    component.major.left.value,
                    "-",
                    component.major.right.value,
                    component.major.left.currency,
                )

    asyncio.run(main())
