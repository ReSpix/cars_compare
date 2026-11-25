import { AlertTriangle, CircleHelp, Gauge, Scale, Sparkles } from 'lucide-react'
import clsx from 'clsx'
import { getComparisonConclusion, getDomesticPrice } from '../utils/comparison'
import { formatNumber } from '../utils/format'

export default function ComparisonConclusion({ report, selection }) {
  const result = getComparisonConclusion(report, selection)
  const domestic = getDomesticPrice(report)
  const warning = result.kind === 'restricted'
  const Icon = warning
    ? AlertTriangle
    : result.kind === 'incomplete'
      ? CircleHelp
      : result.kind === 'close'
        ? Scale
        : Sparkles
  const mileageSamples = [
    {
      label: 'Россия · объявления',
      data: report?.similar_cars,
      total: report?.similar_cars?.bulls?.length ?? 0,
      unit: 'найденных объявлений',
    },
    {
      label: 'Япония · аукционные лоты',
      data: report?.auctions,
      total: report?.auctions?.priced_lot_count ?? 0,
      unit: 'лотов с ценой',
    },
  ]
  return (
    <section
      aria-label="Итог сравнения"
      className={clsx(
        'rounded-2xl border p-5 md:p-6',
        warning ? 'border-amber-200 bg-amber-50' : 'border-border bg-white',
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className={clsx(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
            warning
              ? 'bg-amber-100 text-amber-700'
              : 'bg-brand-light text-brand',
          )}
        >
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="mb-1.5 text-sm font-semibold leading-5 text-muted">
            Что выгоднее в вашем случае · предварительная оценка
          </p>
          <h2 className="text-xl font-bold leading-snug text-dark md:text-2xl">
            {result.title}
          </h2>
          {result.difference != null && (
            <p className="mt-2 text-sm font-semibold text-dark">
              Разница: {formatNumber(result.difference)} ₽ ·{' '}
              {formatNumber(result.percent, 1)}%
            </p>
          )}
        </div>
      </div>
      <p className="mt-4 max-w-4xl text-base leading-7 text-dark">
        {result.description}
      </p>
      {warning && (
        <ul className="mt-3 space-y-1.5 text-sm font-medium leading-6 text-amber-950">
          {result.restrictions.map((reason) => (
            <li key={reason}>• {reason}</li>
          ))}
        </ul>
      )}
      <div
        className="mt-4 grid gap-3 sm:grid-cols-2"
        role="group"
        aria-label="Средний пробег по выборкам"
      >
        {mileageSamples.map(({ label, data, total, unit }) => (
          <div
            key={label}
            className="rounded-xl border border-border bg-white p-4"
          >
            <p className="flex items-center gap-1.5 text-sm font-semibold leading-5 text-muted">
              <Gauge className="h-4 w-4 shrink-0" />
              {label}
            </p>
            <p className="mt-1.5 text-xl font-bold leading-7 text-dark">
              {data?.avg_mileage_km != null
                ? `${formatNumber(data.avg_mileage_km)} км`
                : 'Нет данных о пробеге'}
            </p>
            <p className="mt-1 text-sm leading-6 text-muted">
              Средний пробег · данные для {data?.mileage_count ?? 0} из {total}{' '}
              {unit}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-5 space-y-2.5 border-t border-border pt-4 text-sm leading-6 text-muted">
        <p>
          Цена привоза — до Владивостока. Доставка до вашего города и
          индивидуальные условия оплаты могут изменить итоговую разницу.
        </p>
        {domestic.source === 'listing_average' && (
          <p>
            Цена в России — среднее по {domestic.sampleCount} похожим
            объявлениям, поскольку оценка Drom недоступна. Это цены предложений,
            а не завершённых сделок.
          </p>
        )}
        {report?.japan_import_response && (
          <p>
            Цена лота для калькулятора:{' '}
            {selection.price
              ? 'указана вручную'
              : 'средняя по найденной аукционной выборке'}
            .
          </p>
        )}
        {warning && (
          <details>
            <summary className="cursor-pointer font-semibold text-amber-900">
              Об ограничениях экспорта
            </summary>
            <p className="mt-2">
              Проверка предварительная, по характеристикам выбранной
              модификации. Доставка через другую страну сама по себе не отменяет
              ограничений.
            </p>
          </details>
        )}
      </div>
    </section>
  )
}
