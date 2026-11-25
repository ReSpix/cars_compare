import unittest
from urllib.parse import parse_qs, urlsplit

from app.parser.drom_market import domestic_market_url, parse_market_cards
from app.schemas import SimilarCars


class DromMarketTests(unittest.TestCase):
    def test_search_uses_same_model_year_and_region_in_stock(self):
        source = "https://auto.drom.ru/region25/toyota/rav4/generation5/suv/?w=1&price_stats=1"
        target = urlsplit(domestic_market_url(source, 2020))
        self.assertEqual(target.path, "/region25/toyota/rav4/generation5/suv/")
        self.assertEqual(parse_qs(target.query), {
            "minyear": ["2020"], "maxyear": ["2020"], "whereabouts[]": ["0"], "unsold": ["1"], "w": ["1"],
        })

    def test_cards_are_unique_and_supplement_mileage(self):
        html = "".join(f"""
          <div data-ftid="bulls-list_bull">
            <a href="https://auto.drom.ru/vladivostok/toyota/rav4/{number}.html">
              <img src="https://s1.auto.drom.ru/car.jpg">
            </a>
            <span data-ftid="bull_price">2&nbsp;350&nbsp;000 ₽</span>
            <span data-ftid="bull_location">Владивосток</span>
          </div>
          """ for number in [1, 2, 2, 3, 4])
        cards = parse_market_cards(html, {"1"}, 2)
        self.assertEqual([urlsplit(card["url"]).path.rsplit("/", 1)[1] for card in cards], ["2.html", "3.html"])
        self.assertEqual(cards[0]["price"], 2_350_000)
        self.assertEqual(cards[0]["src"], "https://s1.auto.drom.ru/car.jpg")
        result = SimilarCars(
            searchLink="",
            bulls=[{"url": "primary", "price": 1, "mileage": 10_000}],
            extra_bulls=[{**cards[0], "mileage": 20_000}, cards[1]],
        )
        self.assertEqual(result.mileage_count, 2)
        self.assertEqual(result.avg_mileage_km, 15_000)
