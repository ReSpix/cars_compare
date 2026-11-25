import { Search } from 'lucide-react'
import { getYears } from '../services/api'
import useCatalog from '../hooks/useCatalog'
import SearchableSelect from './SearchableSelect'
import DromSearchButton from './DromSearchButton'

export default function DromSearchPanel({
  selection,
  links,
  range,
  onRangeChange,
}) {
  const { from, to } = range
  const years = useCatalog(
    () => getYears(selection.modelId, selection.wheel),
    `${selection.modelId}:${selection.wheel}`,
    !!selection.modelId,
  )
  const options = [...new Set([selection.year, ...years.items.map(String)])]
    .filter(Boolean)
    .sort((a, b) => Number(b) - Number(a))
    .map((year) => ({ value: year, label: year }))
  const carTitle = [selection.firmTitle, selection.modelTitle]
    .filter(Boolean)
    .join(' ')
  return (
    <section
      aria-label="Поиск предложений на Drom"
      className="rounded-2xl border border-border bg-white p-5 md:p-6"
    >
      <div className="mb-4 flex items-center gap-2">
        <Search className="h-4 w-4 text-brand" />
        <h2 className="font-bold text-dark">
          Найти {carTitle || 'автомобиль'} на Drom
        </h2>
      </div>
      <div className="grid items-start gap-4 lg:grid-cols-[1fr_1fr_2fr]">
        <SearchableSelect
          label="Год от"
          value={from}
          onChange={(from) => onRangeChange({ from, to })}
          options={options}
          error={years.error}
          onRetry={years.retry}
        />
        <SearchableSelect
          label="Год до"
          value={to}
          onChange={(to) => onRangeChange({ from, to })}
          options={options}
        />
        <div className="flex flex-wrap gap-2 lg:pt-6">
          <DromSearchButton
            testId="domestic-search"
            href={links.domestic}
            secondary
          >
            Смотреть объявления в России
          </DromSearchButton>
          <DromSearchButton testId="order-search" href={links.underOrder}>
            Найти автомобиль под заказ
          </DromSearchButton>
        </div>
      </div>
      {links.invalid && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          Год «от» не должен быть позже года «до».
        </p>
      )}
      {!links.domestic && !links.invalid && (
        <p className="mt-3 text-sm leading-6 text-muted">
          Не удалось получить ссылку выбранной модели. Доступен общий раздел
          автомобилей под заказ.
        </p>
      )}
      <p className="mt-3 text-sm leading-6 text-muted">
        Диапазон влияет только на поиск на Drom. Отчёт и карточки ниже
        рассчитаны для {selection.year} года. Подборка на Drom — по модели и
        годам; точная модификация может отличаться.
      </p>
    </section>
  )
}
