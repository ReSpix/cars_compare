import { formatNumber } from '../utils/format'
import { budgetSuggestions } from '../utils/budget'
import SearchableSelect from './SearchableSelect'

const options = budgetSuggestions.map((amount) => ({
  value: String(amount),
  label: `${formatNumber(amount)} ₽`,
}))

export default function BudgetFields({ values, onChange, error, disabled }) {
  return (
    <fieldset disabled={disabled} className="min-w-0 sm:col-span-2">
      <legend className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted">Бюджет</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        <SearchableSelect
          label="Бюджет от"
          value={values.from}
          options={options}
          onChange={(from) => onChange({ ...values, from })}
          placeholder="Бюджет от, ₽"
          disabled={disabled}
          freeInput
          hideLabel
        />
        <SearchableSelect
          label="Бюджет до"
          value={values.to}
          options={options}
          onChange={(to) => onChange({ ...values, to })}
          placeholder="Бюджет до, ₽"
          disabled={disabled}
          freeInput
          hideLabel
        />
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
    </fieldset>
  )
}
