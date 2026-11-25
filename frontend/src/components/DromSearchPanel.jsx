import DromSearchButton from './DromSearchButton'
import { orderSearchLabel } from '../utils/dromLinks'

export default function DromSearchPanel({ links, carTitle, conclusion, preferAlternatives }) {
  const preferred = conclusion === 'incomplete' ? null
    : ['russia', 'restricted'].includes(conclusion) ? 'domestic' : 'order'
  const actions = {
    order: { href: links.underOrder, label: orderSearchLabel(links, carTitle), testId: 'order-search' },
    domestic: { href: links.domestic, label: 'Смотреть объявления в России', testId: 'domestic-search' },
  }
  const order = preferred === 'domestic' ? ['domestic', 'order'] : ['order', 'domestic']
  return (
    <div aria-label="Предложения на Дроме" className="mt-4 grid gap-2 sm:flex sm:flex-wrap">
      {order.map((action) => {
        const { label, ...link } = actions[action]
        return (
          <DromSearchButton key={action} {...link} secondary={preferAlternatives || preferred !== action}>
            {label}
          </DromSearchButton>
        )
      })}
    </div>
  )
}
