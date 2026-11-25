import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  ArrowDown,
  ArrowUp,
  TrendingUp,
  Ship,
  Gavel,
  Images,
  CheckCircle2,
  XCircle,
  Info,
} from 'lucide-react'
import clsx from 'clsx'
import CarSearchForm from '../components/CarSearchForm'
import SearchableSelect from '../components/SearchableSelect'
import AuctionCard from '../components/AuctionCard'
import SimilarCarCard from '../components/SimilarCarCard'
import ImportSection from '../components/ImportSection'
import ComparisonConclusion from '../components/ComparisonConclusion'
import DromSearchPanel from '../components/DromSearchPanel'
import AuctionSampleInfo from '../components/AuctionSampleInfo'
import DromSearchButton from '../components/DromSearchButton'
import DromLink from '../components/DromLink'
import { buildDromSearchLinks, orderSearchLabel } from '../utils/dromLinks'
import { getComparisonConclusion, getDomesticPrice } from '../utils/comparison'
import {
  Spinner,
  ListingResults,
  EmptyState,
  ErrorBanner,
  DegradedBanner,
  Section,
} from '../components/StateBlocks'
import { getCarCompare, sendLog } from '../services/api'
import { trackGoal } from '../services/analytics'
import { compareBudget, parseBudget } from '../utils/budget'
import BudgetFields from '../components/BudgetFields'
import { BudgetStatus, BudgetSummary } from '../components/BudgetResult'
import BudgetAlternatives from '../components/BudgetAlternatives'
import { formatMoney, formatNumber } from '../utils/format'
import {
  AVAILABILITY_LABELS,
  FRAME_LABELS,
  IMPORT_PURPOSES,
  WHEEL_OPTIONS,
} from '../constants/catalog'

function readSelection(searchParams) {
  const get = (key) => searchParams.get(key) || ''
  return {
    firmId: get('firm_id'),
    modelId: get('model_id'),
    year: get('year'),
    modificationId: get('modification_id'),
    generationId: get('generation_id'),
    wheel: get('wheel') || 'UNDEFINED',
    frame: get('frame'),
    regionId: get('region_id') || '0',
    importPurpose: get('import_purpose') || 'USAGE',
    price: get('price'),
    firmTitle: get('firm_title'),
    modelTitle: get('model_title'),
    modificationTitle: get('modification_title'),
    generationTitle: get('generation_title'),
    regionName: get('region_name'),
  }
}

const REPORT_MAX_AGE = 2 * 60 * 60 * 1000

function readDraft(params) {
  return {
    ...readSelection(params),
    from: params.get('budget_min') || '',
    to: params.get('budget_max') || '',
  }
}

export default function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [draft, setDraft] = useState(() => readDraft(searchParams))
  const [formVersion, setFormVersion] = useState(0)
  const [dirty, setDirty] = useState(false)
  const [budgetError, setBudgetError] = useState('')
  const [result, setResult] = useState(null)
  const [failed, setFailed] = useState(null)
  const [loading, setLoading] = useState(false)
  const requestId = useRef(0)
  const activeRequest = useRef(null)

  useEffect(() => {
    function restoreDraft() {
      setDraft(readDraft(new URLSearchParams(window.location.search)))
      setFormVersion((value) => value + 1)
      setDirty(true)
      setBudgetError('')
      setFailed(null)
      requestId.current += 1
      activeRequest.current?.abort()
      activeRequest.current = null
      setLoading(false)
    }
    window.addEventListener('popstate', restoreDraft)
    return () => window.removeEventListener('popstate', restoreDraft)
  }, [])

  const selection = result?.selection ?? draft
  const shownReport = result?.report
  const degraded = Boolean(shownReport?.source_errors?.length)

  function updateDraft(patch) {
    setDraft((previous) => ({ ...previous, ...patch }))
    setDirty(true)
    setBudgetError('')
    setFailed(null)
  }

  function showResult(next) {
    setResult(next)
    setDirty(false)
    if (searchParams.toString() !== next.urlParams.toString()) setSearchParams(next.urlParams)
  }

  async function loadReport(input) {
    if (activeRequest.current) return
    const sequence = ++requestId.current
    const controller = new AbortController()
    activeRequest.current = controller
    setFailed(null)
    trackGoal('comparison_requested')
    const fetched = Date.parse(result?.report?.fetched_at)
    const budgetChanged = result?.budget?.min !== input.budget?.min ||
      result?.budget?.max !== input.budget?.max
    if (result?.key === input.key && budgetChanged && Date.now() - fetched < REPORT_MAX_AGE) {
      showResult({ ...input, report: result.report })
      activeRequest.current = null
      trackGoal('comparison_completed', { result: 'reused' })
      return
    }
    setLoading(true)
    try {
      const data = await getCarCompare(input.params, controller.signal)
      if (sequence !== requestId.current) return
      showResult({ ...input, report: data })
      trackGoal('comparison_completed', { result: data.source_errors?.length ? 'partial' : 'ok' })
    } catch (error) {
      if (sequence !== requestId.current) return
      const message = error.name === 'TimeoutError' ? 'Источники не успели ответить.' : error.message
      setFailed({ message, input, rateLimited: error.status === 429 })
      if (error.status >= 500) sendLog(`car_compare failed: HTTP ${error.status}`).catch(() => {})
      trackGoal('comparison_completed', { result: 'error' })
    } finally {
      if (sequence === requestId.current) {
        activeRequest.current = null
        setLoading(false)
      }
    }
  }

  function applySelection(form) {
    const { budget, error } = parseBudget(draft.from, draft.to)
    if (error) {
      setBudgetError(error)
      return
    }
    const params = {
      firm_id: form.firmId, model_id: form.modelId, year: form.year,
      modification_id: form.modificationId, generation_id: form.generationId,
      wheel: form.wheel, frame: form.frame, region_id: form.regionId,
      import_purpose: draft.importPurpose,
      ...(draft.price ? { price: draft.price } : {}),
    }
    const urlParams = new URLSearchParams({
      ...params,
      firm_title: form.firm?.title || '',
      model_title: form.model?.title || '',
      modification_title: form.modification?.title || '',
      generation_title: form.generation?.title || '',
      region_name: form.region?.name || '',
    })
    if (budget) {
      urlParams.set('budget_max', budget.max)
      if (budget.min) urlParams.set('budget_min', budget.min)
    }
    loadReport({
      params, urlParams, budget, key: new URLSearchParams(params).toString(),
      selection: readSelection(urlParams),
    })
    requestAnimationFrame(() => document.getElementById('report')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  function chooseAlternative(car) {
    setDraft({
      ...selection,
      firmId: String(car.firm_id), modelId: String(car.model_id),
      year: String(Math.max(car.year_from, Math.min(Number(selection.year), car.year_to))),
      wheel: '', generationId: '', modificationId: '', price: '',
      from: result.budget.min ? String(result.budget.min) : '',
      to: String(result.budget.max),
    })
    setFormVersion((value) => value + 1)
    setBudgetError('')
    setFailed(null)
    setDirty(true)
    requestAnimationFrame(() => document.getElementById('search-form')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  const chart = shownReport?.price_change_chart
  const auctions = shownReport?.auctions
  const auctionListings = auctions?.examples?.slice(0, 8) ?? []
  const similar = shownReport?.similar_cars
  const domesticListings = [...(similar?.bulls ?? []), ...(similar?.extra_bulls ?? [])].slice(0, 8)
  const searchLinks = buildDromSearchLinks(similar?.searchLink, selection.year, auctions?.url)
  const carTitle = [selection.firmTitle, selection.modelTitle, selection.year].filter(Boolean).join(' ')
  const conclusion = shownReport ? getComparisonConclusion(shownReport, selection) : null
  const importTotal = shownReport?.japan_import_response?.result?.totalPrice
  const domestic = getDomesticPrice(shownReport)
  const domesticPrice = domestic.value
  const importPrice = importTotal?.currency === 'RUB' ? Number(importTotal.value) : null
  const budgetStatus = result?.budget ? compareBudget(result.budget, domesticPrice, importPrice) : null
  const hasDomesticPrice = domesticPrice !== null
  const hasImportPrice =
    Number.isFinite(importPrice) &&
    importPrice > 0
  const hasComparablePrices = hasDomesticPrice && hasImportPrice
  const availability = shownReport
    ? {
        ...shownReport.results_availability,
        price_change_chart: {
          ...shownReport.results_availability?.price_change_chart,
          available: hasDomesticPrice,
        },
      }
    : null
  const domesticPriceTone = !hasDomesticPrice
    ? 'text-dark'
    : !hasImportPrice
      ? 'text-green-600'
      : domesticPrice > importPrice
        ? 'text-brand'
        : domesticPrice < importPrice
          ? 'text-green-600'
          : 'text-dark'
  const importPriceTone = !hasImportPrice
    ? 'text-dark'
    : !hasDomesticPrice
      ? 'text-green-600'
      : importPrice > domesticPrice
        ? 'text-brand'
        : importPrice < domesticPrice
          ? 'text-green-600'
          : 'text-dark'

  return (
    <div id="top">
      {/* ─── Hero + форма ───────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-br from-darker via-dark to-brand-dark text-white">
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              'radial-gradient(circle at 15% 20%, #e11d2f 0%, transparent 45%), radial-gradient(circle at 85% 10%, #ff7a45 0%, transparent 40%)',
          }}
        />
        <div className="relative max-w-7xl mx-auto px-4 pt-9 pb-20 md:pt-12">
          <div className="max-w-3xl">
            <h1 className="text-balance text-3xl font-extrabold leading-[1.12] tracking-tight md:text-5xl">
              Купить в России или привезти из Японии?
            </h1>
            <p className="mt-3 max-w-2xl text-base text-white/85 md:text-lg">
              Выберите автомобиль. Сравним цены в России и стоимость привоза до
              Владивостока с доставкой и оформлением.
            </p>
          </div>
        </div>
      </section>

      {/* ─── Форма поиска ───────────────────────────────── */}
      <div id="search-form" className="max-w-7xl mx-auto px-4 -mt-12 relative z-10 scroll-mt-20">
        <div className="bg-white rounded-2xl border border-border shadow-2xl shadow-black/10 p-5 md:p-6">
          <h2 className="font-bold text-dark mb-4">Выберите автомобиль</h2>
          <CarSearchForm
            key={formVersion}
            initialSelection={draft}
            disabled={loading}
            onDraftChange={(field, value) =>
              updateDraft(field === 'regionId' ? { regionId: value } : { price: '' })
            }
            onSubmit={applySelection}
          >
            <div className="grid items-start gap-3 border-t border-border pt-4 sm:grid-cols-2 lg:grid-cols-4">
              <BudgetFields values={draft} disabled={loading} error={budgetError} onChange={updateDraft} />
              <SearchableSelect
                label="Цель импорта"
                value={draft.importPurpose}
                options={IMPORT_PURPOSES}
                onChange={(importPurpose) => updateDraft({ importPurpose })}
                disabled={loading}
              />
              <label className="block min-w-0">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                  Цена лота, ¥
                </span>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={draft.price}
                  disabled={loading}
                  onChange={(event) => updateDraft({ price: event.target.value })}
                  placeholder="Средняя по аукционам"
                  className="block w-full rounded-xl border border-border bg-white px-3.5 py-3 text-sm text-dark outline-none transition placeholder:text-muted/80 hover:border-brand/35 focus:border-brand focus:ring-4 focus:ring-brand/10 disabled:cursor-not-allowed disabled:bg-surface disabled:opacity-60"
                />
              </label>
            </div>
          </CarSearchForm>
        </div>
      </div>

      {/* ─── Отчёт ──────────────────────────────────────── */}
      <div id="report" className="max-w-7xl mx-auto px-4 py-10 scroll-mt-20">
        {!shownReport && !failed && !loading && (
          <EmptyState
            title="Рассчитайте стоимость автомобиля"
            text="Выберите марку, модель, год, кузов, поколение и модификацию — отчёт строится по конкретной модификации, потому что от неё зависят объём двигателя, мощность и тип топлива."
          />
        )}

        {loading && (
          <Spinner label="Собираем отчёт: оценка, аукционы, импорт…" />
        )}

        {failed && !loading && (
          <ErrorBanner text={failed.message} onRetry={failed.rateLimited ? undefined : () => loadReport(failed.input)} />
        )}

        {shownReport && (
          <div className="space-y-8">
            {(dirty || loading) && (
              <p role="status" className="rounded-xl border border-border bg-white p-4 text-sm font-medium text-muted">
                Показан предыдущий отчёт. {loading ? 'Готовим новый.' : 'Нажмите «Рассчитать сравнение», чтобы применить изменения.'}
              </p>
            )}
            {/* Шапка отчёта */}
            <div className="bg-white border border-border rounded-2xl p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-dark">
                    {[selection.firmTitle, selection.modelTitle]
                      .filter(Boolean)
                      .join(' ') || 'Отчёт по автомобилю'}
                  </h2>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    <Chip>{selection.year} г.</Chip>
                    <Chip>
                      {FRAME_LABELS[selection.frame] || selection.frame}
                    </Chip>
                    <Chip>
                      {
                        WHEEL_OPTIONS.find((w) => w.value === selection.wheel)
                          ?.label
                      }
                    </Chip>
                    {selection.regionName && (
                      <Chip>{selection.regionName}</Chip>
                    )}
                    {selection.generationTitle && (
                      <Chip>{selection.generationTitle}</Chip>
                    )}
                  </div>
                  {selection.modificationTitle && (
                    <p className="text-sm text-muted mt-2">
                      {selection.modificationTitle}
                    </p>
                  )}
                </div>

                {shownReport.fetched_at && (
                  <p className="text-sm text-muted">
                    Данные обновлены {new Date(shownReport.fetched_at).toLocaleString('ru-RU')}
                  </p>
                )}
              </div>

              {/* Доступность результатов */}
              {availability && (
                <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-border">
                  {Object.entries(availability).map(([key, value]) => (
                    <span
                      key={key}
                      className={clsx(
                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold',
                        value.available
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-brand-light text-brand-dark',
                      )}
                    >
                      {value.available ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <XCircle className="w-3 h-3" />
                      )}
                      {key === 'price_change_chart' &&
                      domestic.source === 'listing_average'
                        ? 'Цена РФ · по объявлениям'
                        : AVAILABILITY_LABELS[key] || key}
                      {!value.available && value.missing_fields?.length > 0 && (
                        <span className="opacity-70 font-normal">
                          · нет: {value.missing_fields.join(', ')}
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {degraded && <DegradedBanner />}

            {/* Оценка цены */}
            {(chart ||
              importTotal ||
              availability?.price_change_chart ||
              availability?.japan_import_response) && (
              <Section
                id="assessment"
                icon={TrendingUp}
                title="Оценка стоимости"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white border border-border rounded-2xl p-6">
                    <div className="mb-3 flex min-h-4 items-center text-xs font-semibold uppercase tracking-wider text-muted">
                      {domestic.source === 'listing_average'
                        ? 'Средняя цена похожих объявлений в РФ'
                        : 'Цена в России'}
                    </div>
                    <div className="flex items-center gap-2 text-3xl font-extrabold tracking-tight tabular-nums sm:text-4xl">
                      <span className={domesticPriceTone}>
                        {hasDomesticPrice
                          ? `${formatNumber(domesticPrice)} ₽`
                          : 'Нет данных'}
                      </span>
                      {hasComparablePrices && domesticPrice > importPrice && (
                        <ArrowUp
                          className="w-6 h-6 text-brand shrink-0"
                          aria-label="Цена выше"
                        />
                      )}
                      {hasComparablePrices && domesticPrice < importPrice && (
                        <ArrowDown
                          className="w-6 h-6 text-green-600 shrink-0"
                          aria-label="Цена ниже"
                        />
                      )}
                    </div>
                    {!hasDomesticPrice && (
                      <p className="text-sm font-semibold text-red-600 mt-3">
                        {chart?.unavailable_reason === 'insufficient_data'
                          ? 'У Drom недостаточно статистики для оценки этой модификации.'
                          : 'Не удалось получить российскую оценку для выбранного автомобиля.'}
                      </p>
                    )}
                    {hasDomesticPrice && (
                      <p className="mt-3 text-sm leading-6 text-muted">
                        {domestic.source === 'listing_average'
                          ? `Средняя по ${domestic.sampleCount} похожим объявлениям на Дроме.`
                          : 'Оценка Дрома для выбранного региона.'}
                      </p>
                    )}
                    <BudgetStatus status={budgetStatus?.russia} />
                  </div>

                  <div className="bg-white border border-border rounded-2xl p-6">
                    <div className="mb-3 flex min-h-4 items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted">
                      <Ship className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
                      Привоз до Владивостока
                    </div>
                    <div className="flex items-center gap-2 text-3xl font-extrabold tracking-tight tabular-nums sm:text-4xl">
                      <span className={importPriceTone}>
                        {hasImportPrice
                          ? formatMoney(importTotal)
                          : 'Нет данных'}
                      </span>
                      {hasComparablePrices && importPrice > domesticPrice && (
                        <ArrowUp
                          className="w-6 h-6 text-brand shrink-0"
                          aria-label="Цена выше"
                        />
                      )}
                      {hasComparablePrices && importPrice < domesticPrice && (
                        <ArrowDown
                          className="w-6 h-6 text-green-600 shrink-0"
                          aria-label="Цена ниже"
                        />
                      )}
                    </div>
                    {!hasImportPrice && (
                      <p className="text-sm font-semibold text-red-600 mt-3">
                        Недостаточно данных для оценки привоза. Можно указать
                        цену конкретного лота.
                      </p>
                    )}
                    {hasImportPrice && (
                      <p className="mt-3 text-sm leading-6 text-muted">С доставкой и оформлением</p>
                    )}
                    <BudgetStatus status={budgetStatus?.japan} />
                  </div>
                </div>
                {budgetStatus?.kind === 'neither' ? (
                  <BudgetAlternatives
                    key={[result.key, result.budget.min, result.budget.max].join(':')}
                    budget={result.budget} selection={selection}
                    disabled={dirty || loading} onSelect={chooseAlternative}
                  />
                ) : (
                  budgetStatus && <BudgetSummary budget={result.budget} kind={budgetStatus.kind} />
                )}
                <DromSearchPanel
                  links={searchLinks} carTitle={carTitle} conclusion={conclusion.kind}
                  preferAlternatives={budgetStatus?.kind === 'neither'}
                />
              </Section>
            )}

            <ComparisonConclusion report={shownReport} conclusion={conclusion} domesticCount={domesticListings.length} />

            {/* Импорт из Японии */}
            <Section
              id="import"
              icon={Ship}
              title="Импорт из Японии"
              subtitle="Доставка, пошлины, утильсбор, НДС и курс ЦБ"
            >
              {shownReport.japan_import_response ? (
                <ImportSection data={shownReport.japan_import_response} />
              ) : (
                <div className="bg-white border border-border rounded-2xl p-6 flex items-start gap-3">
                  <Info className="w-5 h-5 text-brand shrink-0 mt-0.5" />
                  <div className="text-sm text-muted">
                    <p className="font-semibold text-dark mb-1">
                      Расчёт импорта недоступен
                    </p>
                    <p>
                      {shownReport.source_errors?.includes('japan_import_response')
                        ? 'Калькулятор Дрома временно недоступен. Остальные данные отчёта показаны ниже.'
                        : 'Не хватает данных для калькулятора. Укажите цену лота в йенах или выберите другую модификацию.'}
                    </p>
                    {availability?.japan_import_response?.missing_fields
                      ?.length > 0 && (
                      <p className="mt-2 text-xs">
                        Не хватает полей:{' '}
                        <span className="font-mono">
                          {availability.japan_import_response.missing_fields.join(
                            ', ',
                          )}
                        </span>
                      </p>
                    )}
                  </div>
                </div>
              )}
            </Section>

            {/* Аукционы */}
            <Section
              id="auctions"
              icon={Gavel}
              title="Аукционы Японии"
              subtitle={
                auctions?.avg_price_jpy > 0
                  ? `Средняя цена по выборке: ¥${formatNumber(auctions.avg_price_jpy) || '—'}`
                  : 'Лоты с японских аукционов'
              }
            >
              <div className="mb-4 flex flex-col items-start gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4">
                <DromSearchButton testId="auction-order-search" href={searchLinks.underOrder}>
                  {orderSearchLabel(searchLinks, carTitle)}
                </DromSearchButton>
                {auctions?.url && (
                  <DromLink
                    href={auctions.url}
                    placement="auction_statistics"
                    className="rounded px-1 py-2 text-sm font-semibold leading-5 text-muted underline decoration-border underline-offset-4 hover:text-brand-dark focus-visible:outline-2 focus-visible:outline-brand"
                  >
                    Статистика лотов на Дроме
                  </DromLink>
                )}
              </div>
              <ListingResults key={result.key} label="лоты" count={auctionListings.length}>
                <AuctionSampleInfo auctions={auctions} />
                {auctionListings.length ? (
                  <div className="vehicle-card-grid">
                    {auctionListings.map((car, index) => (
                      <AuctionCard key={`${car.url}-${index}`} car={car} />
                    ))}
                  </div>
                ) : (
                  <div className="bg-white border border-border rounded-2xl p-6 text-sm text-muted">
                    По этому запросу лоты не найдены. Попробуйте изменить год или
                    модификацию — фильтры аукциона строятся автоматически.
                  </div>
                )}
              </ListingResults>
            </Section>

            {/* Похожие авто */}
            <Section
              id="similar"
              icon={Images}
              title="Объявления в России"
              subtitle="Предложения российского рынка для сравнения с ценой привоза"
              action={
                <div className="flex w-full flex-col sm:w-auto">
                  <DromSearchButton
                    testId="russia-listings-search"
                    href={searchLinks.domestic}
                  >
                    Смотреть объявления в России
                  </DromSearchButton>
                </div>
              }
            >
              <ListingResults key={result.key} label="объявления" count={domesticListings.length}>
                {domesticListings.length ? (
                  <div className="vehicle-card-grid">
                    {domesticListings.map((bull, index) => (
                      <SimilarCarCard
                        key={`${bull.url}-${index}`}
                        bull={bull}
                        title={[selection.firmTitle, selection.modelTitle].filter(Boolean).join(' ')}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="bg-white border border-border rounded-2xl p-6 text-sm text-muted">
                    Похожих объявлений в России сейчас нет.
                  </div>
                )}
              </ListingResults>
            </Section>
          </div>
        )}
      </div>
    </div>
  )
}

function Chip({ children }) {
  return (
    <span className="text-[11px] font-semibold bg-surface border border-border text-muted rounded-md px-2 py-1">
      {children}
    </span>
  )
}
