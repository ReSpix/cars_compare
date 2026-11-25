import json
import unittest
from urllib.parse import parse_qs, urlsplit

from app.parser.budget_alternatives import (
    AlternativesQuery,
    SourceUnavailable,
    parse_alternatives,
    retry_seconds,
    source_url,
)


QUERY = AlternativesQuery(
    budget_min=800_000, budget_max=2_000_000, year_from=2020,
    year_to=2022, frame="SUV", model_id=100,
)


def group(model_id, min_price, max_price, *, frame=7, year=2021):
    return {
        "groupTitle": f"Model {model_id}",
        "bullListUrl": f"https://auto.drom.ru/test/model{model_id}/?whereabouts[]=2",
        "additionalSearchParams": {"firmId": 1, "modelId": model_id},
        "bullsCount": 5,
        "frameType": frame,
        "minPrice": min_price, "maxPrice": max_price,
        "minYear": year, "maxYear": year,
    }


def page(groups, *, frames=None):
    state = {
        "__slug": "bulls-list-models-range",
        "filter": {"filledParams": {
            "maxPrice": str(QUERY.budget_max), "minYear": QUERY.year_from,
            "maxYear": QUERY.year_to, "frameTypes": [7] if frames is None else frames,
        }},
        "modelRangeData": {"groupingSearchData": groups},
    }
    return "<script type='application/json'>" + json.dumps(state) + "</script>"


class AlternativesTests(unittest.TestCase):
    def test_query_and_ranking_match_filters_without_duplicate_or_source_model(self):
        grouped = [
            group(101, 500_000, 700_000),
            group(102, 950_000, 1_400_000),
            group(102, 950_000, 1_400_000),
            group(100, 950_000, 1_400_000),
            group(103, 950_000, 2_100_000),
            group(104, 950_000, 1_400_000, year=2024),
            group(105, 950_000, 1_400_000, frame=10),
        ]
        self.assertEqual([item.model_id for item in parse_alternatives(page(grouped), QUERY)], [102, 101])
        search = parse_qs(urlsplit(source_url(QUERY)).query)
        self.assertEqual(search, {
            "grouping": ["1"], "whereabouts[]": ["2"], "frametype[]": ["7"],
            "minyear": ["2020"], "maxyear": ["2022"],
        })

    def test_empty_grouped_page_is_distinct_from_bad_source(self):
        self.assertEqual(parse_alternatives(page([]), QUERY), [])
        with self.assertRaises(SourceUnavailable):
            parse_alternatives(page([], frames=[]), QUERY)
        with self.assertRaises(SourceUnavailable):
            parse_alternatives("<html>Дром временно недоступен</html>", QUERY)

    def test_previews_keep_drom_photos_in_source_order(self):
        data = group(101, 1_000_000, 1_400_000)
        photo = "https://s1.auto.drom.ru/photo.jpg"
        data["previews"] = [{}, {"photoUrl": "https://example.org/car.jpg"}, {"photoUrl": photo}]
        result = parse_alternatives(page([data]), QUERY)[0]
        self.assertEqual(result.photo_candidates, [photo])
        self.assertNotIn("photo_candidates", result.model_dump())

    def test_retry_after_defaults_only_when_header_is_missing_or_invalid(self):
        self.assertEqual(retry_seconds("120"), 120)
        self.assertEqual(retry_seconds(None), 60)
        self.assertEqual(retry_seconds("invalid"), 60)
