const counterId = Number(import.meta.env.VITE_METRIKA_COUNTER_ID)
let active = false

export function initializeAnalytics() {
  if (active || !Number.isSafeInteger(counterId) || counterId <= 0) return
  if (['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)) return
  active = true
  window.ym ||= function (...args) {
    ;(window.ym.a ||= []).push(args)
  }
  window.ym.l = Date.now()
  const script = document.createElement('script')
  script.async = true
  script.src = 'https://mc.yandex.ru/metrika/tag.js'
  document.head.append(script)
  window.ym(counterId, 'init', { defer: true, webvisor: false, trackLinks: false })
  window.ym(counterId, 'hit', window.location.origin + window.location.pathname)
}

export function trackGoal(goal, params) {
  if (!active) return
  try {
    window.ym?.(counterId, 'reachGoal', goal, params)
  } catch {
    // Сбой аналитики не должен прерывать действия пользователя.
  }
}
