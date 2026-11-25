import { CalendarDays, Info } from 'lucide-react'

function dateLabel(value) {
  if (!value) return null
  return new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU')
}

export default function AuctionSampleInfo({ auctions }) {
  if (!auctions) return null
  const count = auctions.priced_lot_count
  const dated = auctions.dated_lot_count
  const from = dateLabel(auctions.period_start)
  const to = dateLabel(auctions.period_end)
  const period = from && to ? (from === to ? from : `${from} — ${to}`) : null
  return (
    <div className="mb-4 rounded-xl border border-border bg-white p-4 text-sm leading-6 text-muted">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <span className="font-semibold text-dark">
          Лотов с ценой в расчёте: {count}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <CalendarDays className="h-3.5 w-3.5" />
          {period
            ? `Период выборки: ${period}`
            : count
              ? 'Период выборки: источник не передал даты'
              : 'Период выборки: нет лотов с ценой'}
        </span>
        {period && dated < count && (
          <span className="text-amber-700">
            Даты известны для {dated} из {count} лотов
          </span>
        )}
        {auctions.fetched_at && (
          <span>
            Обновлено:{' '}
            {new Date(auctions.fetched_at).toLocaleString('ru-RU', {
              dateStyle: 'short',
              timeStyle: 'short',
            })}
          </span>
        )}
      </div>
      <details className="mt-3">
        <summary className="inline-flex cursor-pointer items-center gap-1.5 font-semibold text-brand">
          <Info className="h-3.5 w-3.5" />
          Как посчитана средняя цена
        </summary>
        <p className="mt-2 max-w-4xl leading-relaxed">
          Сумма положительных цен в иенах, делённая на число лотов с ценой.
          Период — от самой ранней до самой поздней даты этих лотов на Drom. Это
          загруженная выборка с одной страницы, а не все продажи за указанные
          даты. Подборка учитывает модель, год и объём двигателя; пробег,
          состояние и точная комплектация могут отличаться.
        </p>
      </details>
    </div>
  )
}
