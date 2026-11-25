import { trackGoal } from '../services/analytics'
import { tagDromUrl } from '../utils/dromLinks'

export default function DromLink({ href, placement, children, ...attributes }) {
  const url = tagDromUrl(href, placement)
  if (!url) return null
  const track = () => trackGoal('drom_outbound', { placement, destination: new URL(url).hostname })
  return (
    <a {...attributes} href={url} target="_blank" rel="noopener noreferrer"
      onClick={track} onAuxClick={(event) => { if (event.button === 1) track() }}>
      {children}
    </a>
  )
}
