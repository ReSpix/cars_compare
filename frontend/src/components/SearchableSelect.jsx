import { useId, useState } from 'react'
import {
  Combobox,
  ComboboxButton,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions,
} from '@headlessui/react'
import { Check, ChevronDown, Loader2, RotateCcw } from 'lucide-react'
import clsx from 'clsx'
import { filterOptions, uniqueOptions } from '../utils/selectOptions'

export default function SearchableSelect({
  label,
  value,
  onChange,
  options,
  placeholder = 'Выберите вариант',
  disabled = false,
  loading = false,
  error = false,
  onRetry,
}) {
  const id = useId()
  const [query, setQuery] = useState('')
  const choices = uniqueOptions(options)
  const selected =
    choices.find((option) => option.value === String(value)) ?? null
  const filtered = filterOptions(choices, query)
  return (
    <div className="min-w-0 space-y-1.5">
      <label
        htmlFor={id}
        className="block text-xs font-semibold uppercase tracking-wide text-muted"
      >
        {label}
      </label>
      <Combobox
        immediate
        value={selected}
        by="value"
        disabled={disabled || loading}
        onChange={(option) => {
          if (option) onChange(option.value)
          setQuery('')
        }}
        onClose={() => setQuery('')}
      >
        <div
          className={clsx(
            'relative rounded-xl border bg-white transition focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/10',
            error ? 'border-red-300' : 'border-border hover:border-brand/35',
            (disabled || loading) && 'bg-surface opacity-60',
          )}
        >
          <ComboboxInput
            id={id}
            displayValue={(option) => option?.label ?? ''}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={(event) => event.target.select()}
            placeholder={loading ? 'Загружаем…' : placeholder}
            autoComplete="off"
            className="w-full min-w-0 rounded-xl bg-transparent py-3 pl-3.5 pr-10 text-sm text-dark outline-none placeholder:text-muted/80 disabled:cursor-not-allowed"
          />
          <ComboboxButton
            className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted disabled:cursor-not-allowed"
            aria-label={`Открыть список: ${label}`}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin text-brand" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </ComboboxButton>
        </div>
        <ComboboxOptions
          portal
          anchor={{ to: 'bottom start', gap: 6, padding: 8 }}
          transition
          className="z-50 max-h-72 w-[var(--input-width)] overflow-auto rounded-xl border border-border bg-white p-1.5 shadow-xl shadow-dark/15 outline-none transition duration-100 data-closed:opacity-0"
        >
          {filtered.map((option) => (
            <ComboboxOption
              key={option.value}
              value={option}
              className="group flex cursor-pointer items-start gap-2 rounded-lg px-3 py-2.5 text-sm text-dark data-focus:bg-brand-light data-selected:font-semibold data-selected:text-brand-dark"
            >
              <span className="min-w-0 flex-1 break-words">{option.label}</span>
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand opacity-0 group-data-selected:opacity-100" />
            </ComboboxOption>
          ))}
          {!filtered.length && (
            <div className="px-3 py-4 text-sm text-muted">
              {query ? 'Ничего не найдено' : 'Нет доступных вариантов'}
            </div>
          )}
        </ComboboxOptions>
      </Combobox>
      {error && (
        <div
          className="flex items-center gap-2 text-xs text-red-700"
          role="alert"
        >
          Не удалось загрузить список
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1 font-semibold underline"
            >
              <RotateCcw className="h-3 w-3" />
              Повторить
            </button>
          )}
        </div>
      )}
    </div>
  )
}
