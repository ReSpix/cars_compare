import { useId, useState } from 'react'
import { Loader2, AlertTriangle, ChevronDown, Compass, PlugZap } from 'lucide-react'
import clsx from 'clsx'

export function Spinner({ label = 'Загружаем данные…' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-muted">
      <Loader2 className="w-8 h-8 text-brand animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function EmptyState({ title, text }) {
  return (
    <div className="bg-white border border-dashed border-brand-soft rounded-2xl p-12 text-center">
      <Compass className="w-10 h-10 mx-auto mb-4 text-brand/40" />
      <h3 className="font-bold text-dark text-lg mb-1">{title}</h3>
      <p className="text-sm text-muted max-w-md mx-auto">{text}</p>
    </div>
  )
}

export function ErrorBanner({
  title = 'Не удалось построить отчёт',
  text,
  onRetry,
}) {
  return (
    <div className="bg-brand-light border border-brand-soft rounded-2xl p-5 flex items-start gap-4">
      <AlertTriangle className="w-5 h-5 text-brand-dark shrink-0 mt-0.5" />
      <div className="flex-1">
        <h3 className="font-semibold text-brand-dark text-sm mb-1">{title}</h3>
        <p className="text-sm text-brand-dark/80 break-words">{text}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 text-xs font-semibold text-brand-dark border border-brand-soft rounded-lg px-3 py-2 bg-white hover:bg-brand-light transition-colors"
        >
          Повторить
        </button>
      )}
    </div>
  )
}

export function DegradedBanner() {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-4">
      <PlugZap className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
      <div>
        <h3 className="font-semibold text-amber-900 text-sm mb-1">
          Часть данных недоступна
        </h3>
        <p className="text-sm text-amber-800/80">
          Один из источников Дрома временно не ответил. Доступные результаты показаны ниже.
        </p>
      </div>
    </div>
  )
}

export function Section({ id, icon: Icon, title, subtitle, action, children }) {
  return (
    <section id={id} className="scroll-mt-24 animate-rise">
      <div className="mb-4 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-light flex items-center justify-center shrink-0">
            <Icon className="w-5 h-5 text-brand" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-dark leading-tight">
              {title}
            </h2>
            {subtitle && (
              <p className="text-sm leading-6 text-muted mt-1">{subtitle}</p>
            )}
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export function ListingResults({ label, count, children }) {
  const id = useId()
  const [expanded, setExpanded] = useState(false)

  if (!count) return children

  return (
    <>
      <button
        type="button"
        aria-controls={id}
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        className="mb-3 flex min-h-12 w-full items-center justify-between gap-3 rounded-xl border border-border bg-white px-4 py-3 text-left text-sm font-semibold text-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand sm:hidden"
      >
        <span>{expanded ? `Свернуть ${label}` : `Показать ${label} (${count})`}</span>
        <ChevronDown
          aria-hidden="true"
          className={clsx('h-4 w-4 shrink-0 text-muted transition-transform', expanded && 'rotate-180')}
        />
      </button>
      <div id={id} className={expanded ? undefined : 'hidden sm:block'}>
        {children}
      </div>
    </>
  )
}
