import { AlertTriangle, CircleHelp, Gauge, Scale, Sparkles } from 'lucide-react'
import clsx from 'clsx'
import { formatNumber } from '../utils/format'

const icons = { restricted: AlertTriangle, incomplete: CircleHelp, close: Scale }

export default function ComparisonConclusion({ report, conclusion: result, domesticCount }) {
  const warning = result.kind === 'restricted'
  const Icon = icons[result.kind] || Sparkles
  const samples = [
    {
      label: 'Россия · объявления',
      data: report?.similar_cars,
      total: domesticCount,
    },
    {
      label: 'Япония · аукционные лоты',
      data: report?.auctions,
      total: report?.auctions?.priced_lot_count ?? 0,
    },
  ]
  return (
    <section
      aria-label="Итог сравнения"
      className={clsx(
        'grid gap-4 rounded-2xl border p-5 md:gap-5 md:p-6',
        warning ? 'border-amber-200 bg-amber-50' : 'border-border bg-white',
      )}
    >
      <header className="min-w-0">
        <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-muted">
          <span className={clsx(
            'flex h-7 w-7 shrink-0 items-center justify-center rounded-lg',
            warning ? 'bg-amber-100 text-amber-700' : 'bg-brand-light text-brand',
          )}>
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
          Итог сравнения
        </p>
        <h2 className="text-xl font-bold leading-snug text-dark md:text-2xl">{result.title}</h2>
        {result.difference != null && (
          <p className="mt-2 flex flex-wrap gap-x-1.5 text-sm font-semibold text-dark">
            <span>Разница</span>
            <span className="whitespace-nowrap">{formatNumber(result.difference)} ₽</span>
            <span className="whitespace-nowrap">· {formatNumber(result.percent, 1)}%</span>
          </p>
        )}
      </header>
      {result.note ? (
        <div className="grid gap-3 md:grid-cols-2">
          <div className="min-w-0 rounded-xl bg-surface p-4">
            <h3 className="text-sm font-semibold text-dark">Срок привоза</h3>
            <p className="mt-1 text-sm leading-6 text-muted">{result.description}</p>
          </div>
          <div className="min-w-0 rounded-xl bg-surface p-4">
            <h3 className="text-sm font-semibold text-dark">Что влияет на цену</h3>
            <p className="mt-1 text-sm leading-6 text-muted">{result.note}</p>
          </div>
        </div>
      ) : (
        <div className="max-w-[88ch] text-base leading-7 text-dark">
          <p>{result.description}</p>
          {warning && (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm font-medium leading-6 text-amber-950">
              {result.restrictions.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          )}
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-2" role="group" aria-label="Средний пробег">
        {samples.map(({ label, data, total }) => (
          <div key={label} className="rounded-xl border border-border bg-white p-4">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-muted">
              <Gauge className="h-4 w-4 shrink-0" aria-hidden="true" />
              {label}
            </p>
            <p className="mt-1.5 text-xl font-bold leading-7 text-dark">
              {data?.avg_mileage_km != null
                ? <span className="whitespace-nowrap">{formatNumber(data.avg_mileage_km)} км</span>
                : 'Нет данных о пробеге'}
            </p>
            {total > 0 && (
              <p className="mt-1 text-sm leading-6 text-muted">
                Средний пробег · данные для {data?.mileage_count ?? 0} из {total}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
