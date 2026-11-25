import test from 'node:test'
import assert from 'node:assert/strict'
import { buildDromSearchLinks } from '../src/utils/dromLinks.js'
import {
  getComparisonConclusion,
  getDomesticPrice,
  getImportRestrictions,
} from '../src/utils/comparison.js'
import { filterOptions, uniqueOptions } from '../src/utils/selectOptions.js'

const selection = {
  modificationTitle: '1.5 л, (110 л.с.), бензин',
  frame: 'HATCHBACK',
}
const report = (russia = 2_000_000, japan = 1_500_000) => ({
  price_change_chart: { recommendedPrice: russia },
  japan_import_response: {
    result: { totalPrice: { value: japan, currency: 'RUB' } },
  },
})

test('search preserves region/model and replaces generation and statistical filters with year bounds', () => {
  const links = buildDromSearchLinks(
    'https://auto.drom.ru/region25/toyota/rav4/generation5/restyling0/suv/?w=1&price_stats=1&pts=2',
    { from: '2018', to: '2021' },
  )
  const result = new URL(links.underOrder)
  assert.equal(result.pathname, '/region25/toyota/rav4/')
  assert.equal(result.searchParams.get('whereabouts[]'), '2')
  assert.equal(result.searchParams.get('minyear'), '2018')
  assert.equal(result.searchParams.get('maxyear'), '2021')
  assert.equal(result.searchParams.has('pts'), false)
  assert.deepEqual(
    buildDromSearchLinks(links.domestic, { from: '2022', to: '2020' }),
    { domestic: null, underOrder: null, invalid: true },
  )
  assert.deepEqual(
    buildDromSearchLinks(links.domestic, { from: '', to: '2020' }),
    { domestic: null, underOrder: null, invalid: true },
  )
})

test('domestic search is separate from under-order search', () => {
  const links = buildDromSearchLinks('https://auto.drom.ru/toyota/rav4/', {
    from: '2020',
    to: '2020',
  })
  assert.equal(new URL(links.domestic).searchParams.has('whereabouts[]'), false)
  assert.equal(new URL(links.underOrder).searchParams.get('whereabouts[]'), '2')
})

test('missing or untrusted model links fall back to the Drom order section with the selected years', () => {
  for (const source of [
    undefined,
    'https://example.com/toyota/rav4/',
    'http://auto.drom.ru/toyota/rav4/',
  ]) {
    const links = buildDromSearchLinks(source, { from: '2018', to: '2021' })
    assert.equal(links.domestic, null)
    const result = new URL(links.underOrder)
    assert.equal(result.origin, 'https://auto.drom.ru')
    assert.equal(result.pathname, '/')
    assert.equal(result.searchParams.get('whereabouts[]'), '2')
    assert.equal(result.searchParams.get('minyear'), '2018')
    assert.equal(result.searchParams.get('maxyear'), '2021')
  }
})

test('conclusions distinguish Japan, Russia, close prices, and unavailable/non-RUB totals', () => {
  assert.equal(getComparisonConclusion(report(), selection).kind, 'japan')
  assert.equal(
    getComparisonConclusion(report(2_000_000, 2_500_000), selection).kind,
    'russia',
  )
  assert.equal(
    getComparisonConclusion(report(2_000_000, 1_900_000), selection).kind,
    'close',
  )
  assert.equal(
    getComparisonConclusion(report(null), selection).kind,
    'incomplete',
  )
  assert.equal(
    getComparisonConclusion(report(2_000_000, null), selection).kind,
    'incomplete',
  )
  const foreign = report()
  foreign.japan_import_response.result.totalPrice.currency = 'JPY'
  assert.equal(getComparisonConclusion(foreign, selection).kind, 'incomplete')
})

test('restriction warnings take priority over a cheap estimate or missing price', () => {
  assert.equal(
    getComparisonConclusion(report(), {
      ...selection,
      modificationTitle: '2.0 л, бензин',
    }).kind,
    'restricted',
  )
  assert.equal(
    getComparisonConclusion(
      {},
      { ...selection, modificationTitle: '1.5 л, гибрид' },
    ).kind,
    'restricted',
  )
  assert.equal(
    getImportRestrictions(
      {},
      { ...selection, modificationTitle: '1.9 л, бензин' },
    ).length,
    0,
  )
  const changed = { auctions: { avg_price_jpy: 7_000_000 } }
  assert.equal(
    getImportRestrictions(changed, {
      ...selection,
      price: '2_000_000'.replaceAll('_', ''),
    }).length,
    0,
  )
  assert.equal(getImportRestrictions(changed, selection).length, 1)
})

test('search deduplicates numeric/string ids, ignores case and ё, and prioritizes prefix matches', () => {
  const options = uniqueOptions([
    { value: 9, label: 'Toyota' },
    { value: '9', label: 'Toyota' },
    { value: 2, label: 'Новая Toyota' },
    { value: 3, label: 'Бёрн' },
  ])
  assert.equal(options.length, 3)
  assert.deepEqual(
    filterOptions(options, 'TOY').map((item) => item.value),
    ['9', '2'],
  )
  assert.equal(filterOptions(options, 'бер')[0].label, 'Бёрн')
  assert.equal(filterOptions(options, 'no-match').length, 0)
})

test('missing Drom estimates fall back to distinct listings with positive prices', () => {
  const data = {
    ...report(null),
    similar_cars: {
      bulls: [
        { url: 'a', price: 4_500_000 },
        { url: 'b', price: 3_700_000 },
        { url: 'c', price: 3_420_000 },
        { url: 'd', price: 3_700_000 },
        { url: 'a', price: 4_500_000 },
        { url: 'e', price: 0 },
        { url: 'f', price: null },
        { url: 'g', price: 'invalid' },
      ],
    },
  }
  assert.deepEqual(getDomesticPrice(data), {
    value: 3_830_000,
    source: 'listing_average',
    sampleCount: 4,
  })
  assert.equal(getComparisonConclusion(data, selection).kind, 'japan')
  data.price_change_chart.recommendedPrice = 2_000_000
  assert.deepEqual(getDomesticPrice(data), {
    value: 2_000_000,
    source: 'drom_estimate',
    sampleCount: null,
  })
})

test('an empty listing sample never becomes a zero-ruble estimate', () => {
  const data = {
    ...report(null),
    similar_cars: { bulls: [{ url: 'a', price: 0 }] },
  }
  assert.deepEqual(getDomesticPrice(data), {
    value: null,
    source: null,
    sampleCount: 0,
  })
  assert.equal(getComparisonConclusion(data, selection).kind, 'incomplete')
})

test('a small-engine Prius warning explains the Japanese export restriction', () => {
  const result = getComparisonConclusion(report(), {
    modificationTitle: '1.8 л, (98 л.с.), бензин, гибрид',
    frame: 'LIFTBACK',
  })
  assert.equal(result.kind, 'restricted')
  assert.match(result.title, /экспорта из Японии/)
  assert.match(result.description, /не означает запрет на покупку/)
  assert.match(result.restrictions[0], /до 1,9 л/)
})
