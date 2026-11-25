import { useEffect, useEffectEvent, useState } from 'react'

/** Ответ предыдущего выбора не должен заменять текущий каталог. */
export default function useCatalog(loader, key, enabled = true) {
  const loadItems = useEffectEvent(loader)
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState({
    key: null,
    attempt: -1,
    items: [],
    error: false,
  })
  useEffect(() => {
    if (!enabled) return
    let current = true
    Promise.resolve()
      .then(() => {
        if (current) return loadItems()
      })
      .then(
        (items) => {
          if (current) setState({ key, attempt, items, error: false })
        },
        () => {
          if (current) setState({ key, attempt, items: [], error: true })
        },
      )
    return () => {
      current = false
    }
  }, [key, enabled, attempt])
  const matches = enabled && state.key === key && state.attempt === attempt
  return {
    items: matches ? state.items : [],
    loading: enabled && !matches,
    error: matches && state.error,
    retry: () => setAttempt((value) => value + 1),
  }
}
