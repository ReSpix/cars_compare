import { useState } from 'react'
import { CarFront, ExternalLink } from 'lucide-react'
import DromLink from './DromLink'
import { tagDromUrl } from '../utils/dromLinks'

function VehiclePhoto({ src, title }) {
  const [failed, setFailed] = useState(false)
  return (
    <div className="flex aspect-[4/3] items-center justify-center overflow-hidden bg-surface">
      {src && !failed ? (
        <img
          src={src}
          alt={title}
          loading="lazy"
          decoding="async"
          onError={() => setFailed(true)}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
      ) : (
        <CarFront className="h-10 w-10 text-muted/45" role="img" aria-label="Фото недоступно" />
      )}
    </div>
  )
}

export default function VehicleCard({
  title, image, price, source, details = [], href, placement, linkLabel, children,
}) {
  const body = (
    <>
      <VehiclePhoto key={image} src={image} title={title} />
      <div className="flex flex-1 flex-col px-4 py-3">
        <p className="text-xs font-medium text-muted">{source}</p>
        <h3 className="mt-1 text-sm font-semibold leading-snug text-dark">{title}</h3>
        <p className="mt-1.5 text-base font-extrabold leading-snug text-dark">{price}</p>
        {details.length > 0 && (
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {details.map((detail) => (
              <li key={detail} className="rounded-md bg-surface px-2 py-1 text-xs leading-4 text-muted">{detail}</li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
  return (
    <article className="group flex h-full min-w-0 flex-col overflow-hidden rounded-xl border border-border bg-white transition hover:border-brand/35 hover:shadow-md">
      {tagDromUrl(href, placement) ? (
        <DromLink
          href={href} placement={placement}
          className="flex flex-1 flex-col no-underline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand"
        >
          {body}
          <span className="flex items-center justify-between gap-2 border-t border-border px-4 py-2.5 text-xs font-semibold text-brand-dark transition group-hover:bg-brand-light">
            {linkLabel}<ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          </span>
        </DromLink>
      ) : body}
      {children}
    </article>
  )
}
