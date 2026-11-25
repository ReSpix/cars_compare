/**
 * Клиент Cars Compare API.
 *
 * Все пути относительные — Vite проксирует их на бэкенд, поэтому
 * CORS не мешает ни в dev, ни в preview.
 */

async function request(path, params = {}, { timeout, signal, ...options } = {}) {
  const url = new URL(path, window.location.origin)
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, value)
    }
  })

  const controller = timeout ? new AbortController() : null
  const abort = () => controller.abort()
  let timedOut = false
  const timer = controller && window.setTimeout(() => {
    timedOut = true
    abort()
  }, timeout)
  if (controller) {
    if (signal?.aborted) abort()
    else signal?.addEventListener('abort', abort, { once: true })
  }
  try {
    const response = await fetch(url, { ...options, signal: controller?.signal ?? signal })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const detail = body.detail
      const error = new Error(
        typeof detail === 'string' ? detail : detail?.message || `Ошибка запроса (${response.status})`,
      )
      error.status = response.status
      error.sourceUrl = detail?.source_url
      error.retryAfter = Number(response.headers.get('Retry-After')) || 0
      throw error
    }
    return await response.json()
  } catch (error) {
    if (timedOut) throw new DOMException('Время ожидания истекло', 'TimeoutError')
    throw error
  } finally {
    if (controller) {
      window.clearTimeout(timer)
      signal?.removeEventListener('abort', abort)
    }
  }
}

// ─── Справочники ──────────────────────────────────────────
export const getRegions = () => request('/regions')

// ─── Каталог rate-car ─────────────────────────────────────
export const getFirms = () => request('/rate-car/firms')
export const getModels = (firmId) => request('/rate-car/models', { firm_id: firmId })
export const getYears = (modelId, wheel) =>
  request('/rate-car/years', { model_id: modelId, wheel })
export const getFrames = (modelId, year, wheel) =>
  request('/rate-car/frames', { model_id: modelId, year, wheel })
export const getGenerations = (modelId, year, frame, wheel) =>
  request('/rate-car/generations', { model_id: modelId, year, frame, wheel })
export const getModifications = (modelId, year, frame, generationId, wheel) =>
  request('/rate-car/modifications', {
    model_id: modelId,
    year,
    frame,
    generation_id: generationId,
    wheel,
  })

// ─── Комбинированный отчёт ────────────────────────────────
export const getCarCompare = (params, signal) => request('/car_compare', params, { signal, timeout: 72_000 })
export const getBudgetAlternatives = (params) => request('/budget-alternatives', {}, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(params),
  timeout: 60_000,
})

// ─── Журнал сервера ───────────────────────────────────────
export async function sendLog(message) {
  const response = await fetch('/log', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: message,
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
