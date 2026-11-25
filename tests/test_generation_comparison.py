import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import aiohttp

from app.parser import car_rate, combined_compare
from app.schemas import (
    CarCompareQuery,
    Firm,
    Model,
    Modification,
    PriceChangeChart,
    SimilarCars,
)


GEN_5 = SimpleNamespace(id="16707", value="5_0", generationNumber=5, restylingNumber=0)
GEN_4 = SimpleNamespace(
    id="9313_13041", value="4_1", generationNumber=4, restylingNumber=1
)
MOD = Modification(id=3238, title="1.8 л, (98 л.с.), бензин, гибрид")
PARAMS = dict(
    firm_id=9,
    model_id=223,
    year=2022,
    modification_id=3238,
    wheel="LEFT",
    frame="LIFTBACK",
    region_id=0,
    generation_id=GEN_4.id,
)


class GenerationComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        car_rate._catalog_cache.clear()

    async def test_shared_modification_id_uses_the_selected_generation(self):
        with (
            patch.object(
                car_rate, "get_generations_list", AsyncMock(return_value=[GEN_5, GEN_4])
            ),
            patch.object(
                car_rate, "get_modifications_list", AsyncMock(return_value=[MOD])
            ) as mods,
            patch.object(
                car_rate,
                "_rest_get",
                AsyncMock(return_value={"recommendedPrice": 1970000}),
            ) as rest,
        ):
            result = await car_rate.get_price_change_chart(**PARAMS)
            await car_rate.get_price_change_chart(**PARAMS)
        self.assertEqual(result.recommendedPrice, 1970000)
        self.assertEqual(mods.await_count, 1)
        self.assertEqual(mods.await_args.kwargs["generation_value"], "4_1")
        sent = rest.await_args.args[1]
        self.assertEqual((sent["generationNumber"], sent["restylingNumber"]), (4, 1))

    async def test_invalid_generation_does_not_fall_back_to_another_generation(self):
        with (
            patch.object(
                car_rate, "get_generations_list", AsyncMock(return_value=[GEN_5, GEN_4])
            ),
            patch.object(
                car_rate, "get_modifications_list", AsyncMock(return_value=[MOD])
            ) as mods,
        ):
            with self.assertRaises(LookupError):
                await car_rate.get_generation_and_modification(
                    223, 2022, "LIFTBACK", "LEFT", 3238, generation_id="unknown"
                )
        mods.assert_not_awaited()

    async def test_missing_statistics_and_an_unavailable_source_have_different_reasons(
        self,
    ):
        for status, reason in [(400, "insufficient_data"), (503, "source_unavailable")]:
            with (
                self.subTest(status=status),
                patch.object(
                    car_rate,
                    "get_generation_and_modification",
                    AsyncMock(return_value=(GEN_4, MOD)),
                ),
                patch.object(
                    car_rate,
                    "_rest_get",
                    AsyncMock(
                        side_effect=aiohttp.ClientResponseError(None, (), status=status)
                    ),
                ),
            ):
                result = await car_rate.get_price_change_chart(**PARAMS)
                self.assertIsNone(result.recommendedPrice)
                self.assertEqual(result.unavailable_reason, reason)

    async def test_combined_report_forwards_generation_and_marks_empty_results_unavailable(
        self,
    ):
        query = CarCompareQuery(**PARAMS, import_purpose="USAGE")
        with (
            patch.object(
                combined_compare,
                "get_firms_list",
                AsyncMock(return_value=[Firm(id=9, title="Toyota")]),
            ),
            patch.object(
                combined_compare,
                "get_models_list",
                AsyncMock(return_value=[Model(id=223, title="Prius", wheels=["LEFT"])]),
            ),
            patch.object(
                combined_compare,
                "get_generation_and_modification",
                AsyncMock(return_value=(GEN_4, MOD)),
            ) as resolve,
            patch.object(
                combined_compare,
                "get_price_change_chart",
                AsyncMock(
                    return_value=PriceChangeChart(
                        unavailable_reason="insufficient_data"
                    )
                ),
            ) as chart,
            patch.object(
                combined_compare,
                "get_similar_cars",
                AsyncMock(
                    return_value=SimilarCars(
                        searchLink="https://auto.drom.ru/toyota/prius/"
                    )
                ),
            ) as similar,
            patch.object(combined_compare, "parse_auction", AsyncMock(return_value=[])),
        ):
            result = await combined_compare.get_combined_compare(query)
        for call in [resolve, chart, similar]:
            self.assertEqual(call.await_args.kwargs["generation_id"], GEN_4.id)
        self.assertFalse(result.results_availability.price_change_chart.available)
        self.assertFalse(result.results_availability.similar_cars.available)
        self.assertFalse(result.results_availability.auctions.available)
        self.assertFalse(result.results_availability.japan_import_response.available)


if __name__ == "__main__":
    unittest.main()
