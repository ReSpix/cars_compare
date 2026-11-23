from __future__ import annotations

import asyncio
import json

import aiohttp
from pydantic import ValidationError

from app.schemas import (
    Currency,
    EngineType,
    ImportPurpose,
    JapanImportRequest,
    JapanImportResponse,
    Money,
    MoneyRange,
    VehicleAge,
)

# ============================================================
# CONFIG
# ============================================================

API_URL = "https://www.drom.ru/api/world/calculate/japan/"

DEFAULT_TIMEOUT = 20

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
            price_jpy=1_000_000,
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
