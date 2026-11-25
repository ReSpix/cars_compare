import test from 'node:test'
import assert from 'node:assert/strict'
import { budgetSuggestions, compareBudget, parseBudget } from '../src/utils/budget.js'
import { tagDromUrl } from '../src/utils/dromLinks.js'

test('both budget fields have all 35 suggestions and accept custom amounts', () => {
  assert.deepEqual(budgetSuggestions, Array.from({ length: 35 }, (_, i) => 300000 + i * 50000))
  assert.deepEqual(parseBudget('450\u202f000', '3 830 000').budget, { min: 450000, max: 3830000 })
  assert.deepEqual(parseBudget('', '300000').budget, { min: 0, max: 300000 })
  assert.deepEqual(parseBudget('', ''), { budget: null })
  for (const [min, max] of [['500000', ''], ['500000', '300000'], ['', 'abc'], ['', '0']]) {
    assert.ok(parseBudget(min, max).error)
  }
})

test('both prices at or below the maximum fit, including below the minimum', () => {
  const budget = { min: 800000, max: 1000000 }
  assert.deepEqual(compareBudget(budget, 750000, 1000000), {
    kind: 'both',
    russia: { kind: 'below', amount: 250000 },
    japan: { kind: 'fits', amount: 0 },
  })
  assert.equal(compareBudget(budget, 1000010, 1200000).kind, 'neither')
  assert.equal(compareBudget(budget, 1000010, 900000).kind, 'japan')
  assert.equal(compareBudget(budget, 900000, null).kind, 'russia')
  assert.equal(compareBudget(budget, null, 1200000).kind, 'unknown')
})

test('UTM tags preserve Drom search filters and reject foreign destinations', () => {
  const original = 'https://auto.drom.ru/do-2000000/?grouping=1&whereabouts%5B%5D=2&minyear=2022'
  const tagged = new URL(tagDromUrl(original, 'budget_search'))
  assert.equal(tagged.pathname, '/do-2000000/')
  assert.equal(tagged.searchParams.get('grouping'), '1')
  assert.equal(tagged.searchParams.get('whereabouts[]'), '2')
  assert.equal(tagged.searchParams.get('minyear'), '2022')
  assert.equal(tagged.searchParams.get('utm_source'), 'cars_compare')
  assert.equal(tagged.searchParams.get('utm_medium'), 'referral')
  assert.equal(tagged.searchParams.get('utm_campaign'), 'mvp')
  assert.equal(tagged.searchParams.get('utm_content'), 'budget_search')
  assert.equal(tagDromUrl('https://auto.drom.ru.example.org/', 'budget_search'), null)
})
