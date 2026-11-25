import json
import unittest
from datetime import date

from app.schemas import AuctionQuery, AuctionResponse, Bull, Car, SimilarCars
from app.parser.listing_mileage import parse_listing_mileage


class AuctionStatisticsTests(unittest.TestCase):
    def response(self, cars):
        return AuctionResponse(
            query=AuctionQuery(firm="toyota", model="rav4"),
            url="https://www.drom.ru/world/japan/toyota/rav4/",
            examples=cars,
        )

    def test_jpy_offer_date_is_used_instead_of_production_year_or_rub_offer(self):
        car = Car.from_json_ld(
            {
                "name": "Toyota RAV4",
                "productionDate": "2020",
                "offers": [
                    {
                        "priceCurrency": "RUB",
                        "price": 3000000,
                        "validFrom": "2026-11-25",
                    },
                    {
                        "priceCurrency": "JPY",
                        "price": 2000000,
                        "validFrom": "2026-11-14",
                    },
                ],
            }
        )
        self.assertEqual(car.year, 2020)
        self.assertEqual(car.auction_date, date(2026, 11, 14))
        self.assertEqual(car.price_jpy, 2000000)

    def test_period_and_average_only_include_lots_with_positive_prices(self):
        result = self.response(
            [
                Car(name="A", price_jpy=100, auction_date="2026-11-21"),
                Car(name="B", price_jpy=200, auction_date="2026-11-14"),
                Car(name="C", price_jpy=0, auction_date="2020-01-01"),
                Car(name="D", price_jpy=None, auction_date="2027-01-01"),
            ]
        )
        self.assertEqual(result.avg_price_jpy, 150)
        self.assertEqual(result.priced_lot_count, 2)
        self.assertEqual(result.dated_lot_count, 2)
        self.assertEqual(result.period_start, date(2026, 11, 14))
        self.assertEqual(result.period_end, date(2026, 11, 21))

    def test_missing_invalid_and_partial_dates_do_not_invent_a_period(self):
        invalid = Car(name="A", price_jpy=100, auction_date="not-a-date")
        result = self.response(
            [invalid, Car(name="B", price_jpy=300, auction_date="2026-11-20")]
        )
        self.assertEqual(result.avg_price_jpy, 200)
        self.assertEqual(result.priced_lot_count, 2)
        self.assertEqual(result.dated_lot_count, 1)
        self.assertEqual(result.period_start, result.period_end)
        undated = self.response([invalid])
        self.assertIsNone(undated.period_start)
        self.assertIsNone(undated.period_end)
        empty = self.response([])
        self.assertEqual(empty.avg_price_jpy, 0)
        self.assertEqual(empty.priced_lot_count, 0)
        self.assertIsNotNone(empty.fetched_at.tzinfo)

    def test_mileage_averages_exclude_missing_values_but_keep_explicit_zero(self):
        domestic = SimilarCars(
            searchLink="https://auto.drom.ru/toyota/rav4/",
            bulls=[
                Bull(url="https://auto.drom.ru/a.html", price=100, mileage=100000),
                Bull(url="https://auto.drom.ru/b.html", price=200, mileage=0),
                Bull(url="https://auto.drom.ru/c.html", price=300),
            ],
        )
        self.assertEqual(domestic.avg_mileage_km, 50000)
        self.assertEqual(domestic.mileage_count, 2)
        auction = self.response(
            [
                Car(name="A", price_jpy=100, mileage=100000),
                Car(name="B", price_jpy=200, mileage=0),
                Car(name="C", price_jpy=300),
                Car(name="D", price_jpy=0, mileage=999999),
            ]
        )
        self.assertEqual(auction.avg_mileage_km, 50000)
        self.assertEqual(auction.mileage_count, 2)
        self.assertIsNone(self.response([]).avg_mileage_km)
        self.assertIsNone(
            SimilarCars(searchLink="https://auto.drom.ru/").avg_mileage_km
        )

    def test_mileage_parser_requires_explicit_kilometres_and_a_matching_listing(self):
        def page(value, unit="KMT", url="https://auto.drom.ru/a.html"):
            data = {
                "@type": "Car",
                "offers": {"url": url},
                "mileageFromOdometer": {"value": value, "unitCode": unit},
            }
            return (
                '<script type="application/ld+json">' + json.dumps(data) + "</script>"
            )

        self.assertEqual(parse_listing_mileage(page("86\u00a0000")), 86000)
        self.assertEqual(parse_listing_mileage(page(0)), 0)
        self.assertIsNone(parse_listing_mileage(page(None)))
        self.assertIsNone(parse_listing_mileage(page(-100)))
        self.assertIsNone(parse_listing_mileage(page(100, "SMI")))
        self.assertIsNone(
            parse_listing_mileage(page(100), expected_url="https://auto.drom.ru/b.html")
        )
        self.assertIsNone(
            parse_listing_mileage('<script type="application/ld+json">invalid</script>')
        )


if __name__ == "__main__":
    unittest.main()
