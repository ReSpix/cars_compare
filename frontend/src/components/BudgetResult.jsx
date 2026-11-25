import clsx from 'clsx'
import { formatNumber } from '../utils/format'

const summaries = {
  both: 'Оба варианта укладываются в бюджет',
  russia: 'Покупка в России укладывается в бюджет',
  japan: 'Расчёт привоза укладывается в бюджет',
  neither: 'Оба варианта дороже вашего бюджета',
  unknown: 'Для сравнения с бюджетом пока не хватает данных',
}

export function BudgetStatus({ status }) {
  if (!status || status.kind === 'unknown') return null
  const amount = `${formatNumber(status.amount)} ₽`
  if (status.kind === 'over') {
    return <p className="mt-3 text-sm font-semibold text-brand-dark">Не хватает <span className="whitespace-nowrap">{amount}</span></p>
  }
  return (
    <p className="mt-3 text-sm font-semibold text-emerald-800">
      {status.kind === 'below' ? 'Дешевле заданного диапазона' : 'Укладывается в бюджет'}
      {status.amount > 0 && <span className="ml-2 inline-block font-normal">Остаётся {amount}</span>}
    </p>
  )
}

export function BudgetSummary({ budget, kind, children }) {
  const amount = budget.min
    ? `${formatNumber(budget.min)}–${formatNumber(budget.max)} ₽`
    : `до ${formatNumber(budget.max)} ₽`
  return (
    <section
      aria-label="Сравнение с бюджетом"
      className={clsx(
        'mt-4 rounded-2xl border px-4 py-4 sm:px-5',
        kind === 'neither' ? 'border-brand-soft bg-brand-light' : 'border-border bg-white',
      )}
    >
      <h3 className="text-base font-bold leading-snug text-dark">{summaries[kind]}</h3>
      <div className="mt-2 flex flex-col items-start gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4">
        <p className="text-sm leading-6 text-muted">
          Бюджет <strong className="whitespace-nowrap text-dark">{amount}</strong>
        </p>
        {children}
      </div>
    </section>
  )
}
