import { useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { getBudgetAlternatives } from '../services/api'
import { formatNumber } from '../utils/format'
import DromSearchButton from './DromSearchButton'
import { BudgetSummary } from './BudgetResult'
import VehicleCard from './VehicleCard'
import { trackGoal } from '../services/analytics'

const frameCodes = {
  OPEN: 11, COUPE: 1, SUV: 7, HATCHBACK: 5, SEDAN: 10,
  MINIVAN_2_ROW_SEATS: 6, MINIVAN_3_ROW_SEATS: 6, WAGON: 3,
  PICKUP: 12, HATCHBACK_3DR: 4, SUV_3DR: 8, LIFTBACK: 9,
}

function fallbackLink(budget, selection) {
  const url = new URL(`https://auto.drom.ru/do-${budget.max}/`)
  url.searchParams.set('grouping', '1')
  url.searchParams.set('whereabouts[]', '2')
  url.searchParams.set('minyear', selection.year)
  url.searchParams.set('maxyear', selection.year)
  if (frameCodes[selection.frame]) url.searchParams.set('frametype[]', frameCodes[selection.frame])
  return url.href
}

export default function BudgetAlternatives({ budget, selection, disabled, onSelect }) {
  const [state, setState] = useState({ loading: false })
  const inFlight = useRef(false)
  const [cooldown, setCooldown] = useState(0)
  useEffect(() => {
    if (!cooldown) return
    const timer = window.setTimeout(() => setCooldown(0), Math.min(cooldown * 1000, 2_147_483_647))
    return () => window.clearTimeout(timer)
  }, [cooldown])

  async function find() {
    if (inFlight.current || cooldown || disabled) return
    inFlight.current = true
    setState({ loading: true })
    trackGoal('alternatives_requested')
    try {
      const result = await getBudgetAlternatives({
        budget_min: budget.min, budget_max: budget.max,
        frame: selection.frame, model_id: Number(selection.modelId),
        year_from: Number(selection.year), year_to: Number(selection.year),
      })
      setState({ result, loading: false })
      trackGoal('alternatives_completed', { result: result.status })
    } catch (error) {
      setCooldown(error.retryAfter || 0)
      setState({
        loading: false,
        error: error.name === 'TimeoutError' ? 'Дром не успел ответить.' : error.message,
        sourceUrl: error.sourceUrl,
      })
      trackGoal('alternatives_completed', { result: 'error' })
    } finally {
      inFlight.current = false
    }
  }

  const { result } = state
  const source = result?.source_url || state.sourceUrl || fallbackLink(budget, selection)
  return (
    <div aria-busy={state.loading}>
      <BudgetSummary budget={budget} kind="neither">
        <button
          type="button"
          disabled={state.loading || Boolean(cooldown) || disabled}
          onClick={find}
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-center text-sm font-semibold leading-5 text-white hover:bg-brand-dark focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand disabled:opacity-60"
        >
          <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
          {state.loading ? 'Ищем на Дроме…' : 'Подобрать другие модели'}
        </button>
      </BudgetSummary>
      <div aria-live="polite">
        {(result || state.error) && (
          <div className="mt-3">
            <DromSearchButton secondary href={source} placement="budget_search">Открыть подбор на Дроме</DromSearchButton>
          </div>
        )}
        {state.error && <p className="mt-3 text-sm text-brand-dark">{state.error}</p>}
        {result?.status === 'empty' && <p className="mt-3 text-sm text-muted">На первой странице Дрома подходящих моделей не найдено.</p>}
        {result?.status === 'unsupported_frame' && <p className="mt-3 text-sm text-muted">В подборе Дрома нет фильтра для этого кузова. Ссылка откроет поиск по бюджету и выбранному году.</p>}
        {Boolean(result?.items.length) && (
          <>
            <p className="mt-3 text-sm text-muted">
              Под заказ · {selection.year} г. · тот же тип кузова
              {' · '}Обновлено {new Date(result.fetched_at).toLocaleString('ru-RU')}
            </p>
            <div className="vehicle-card-grid mt-3">
              {result.items.map((car) => (
                <VehicleCard
                  key={car.model_id} title={car.title} image={car.photo} source="Под заказ"
                  price={`${formatNumber(car.price_from)}${car.price_to !== car.price_from ? `–${formatNumber(car.price_to)}` : ''} ₽`}
                  details={[`${selection.year} г.`, `${formatNumber(car.count)} объявл.`]}
                  href={car.url} placement="budget_model" linkLabel="Смотреть под заказ"
                >
                  <button type="button" disabled={disabled} onClick={() => onSelect(car)}
                    className="border-t border-border px-4 py-2.5 text-left text-xs font-semibold text-brand-dark hover:bg-brand-light disabled:opacity-60">
                    Сравнить эту модель
                  </button>
                </VehicleCard>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
