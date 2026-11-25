import { ExternalLink } from 'lucide-react'
import clsx from 'clsx'

export default function DromSearchButton({
  href,
  children,
  secondary = false,
  testId,
}) {
  if (!href) return null
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      data-testid={testId}
      className={clsx(
        'inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 py-3 text-center text-sm font-semibold leading-5 no-underline transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand',
        secondary
          ? 'border border-border bg-white text-dark hover:border-brand/40 hover:bg-brand-light'
          : 'bg-brand text-white hover:bg-brand-dark',
      )}
    >
      {children}
      <ExternalLink className="h-4 w-4 shrink-0" aria-hidden="true" />
    </a>
  )
}
