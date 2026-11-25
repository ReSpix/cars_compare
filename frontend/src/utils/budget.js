export const budgetSuggestions = Array.from(
  { length: 35 },
  (_, index) => 300_000 + index * 50_000,
)

function parseAmount(value) {
  const digits = String(value ?? '').replace(/\s/g, '')
  if (!digits) return null
  const amount = Number(digits)
  return /^\d+$/.test(digits) && Number.isSafeInteger(amount) ? amount : NaN
}

export function parseBudget(from, to) {
  const min = parseAmount(from)
  const max = parseAmount(to)
  if (min === null && max === null) return { budget: null }
  if (Number.isNaN(min) || Number.isNaN(max)) {
    return { error: 'Введите целую сумму в рублях.' }
  }
  if (max === null || max === 0) {
    return { error: 'Укажите положительную верхнюю границу бюджета.' }
  }
  if (min > max) return { error: 'Бюджет «от» не может быть больше бюджета «до».' }
  return { budget: { min: min ?? 0, max } }
}

function priceStatus(value, { min, max }) {
  if (!Number.isFinite(value) || value <= 0) return { kind: 'unknown' }
  const remaining = Math.round(max - value)
  return {
    kind: value > max ? 'over' : value < min ? 'below' : 'fits',
    amount: Math.abs(remaining),
  }
}

export function compareBudget(budget, domestic, imported) {
  const russia = priceStatus(domestic, budget)
  const japan = priceStatus(imported, budget)
  const fits = (status) => status.kind === 'fits' || status.kind === 'below'
  let kind = 'unknown'
  if (fits(russia) && fits(japan)) kind = 'both'
  else if (fits(russia)) kind = 'russia'
  else if (fits(japan)) kind = 'japan'
  else if (russia.kind === 'over' && japan.kind === 'over') kind = 'neither'
  return { kind, russia, japan }
}
