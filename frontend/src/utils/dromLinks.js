export function tagDromUrl(href, placement) {
  try {
    const url = new URL(href)
    if (url.protocol !== 'https:' || url.username || url.password ||
        !['drom.ru', 'www.drom.ru', 'auto.drom.ru'].includes(url.host)) return null
    url.searchParams.set('utm_source', 'cars_compare')
    url.searchParams.set('utm_medium', 'referral')
    url.searchParams.set('utm_campaign', 'mvp')
    url.searchParams.set('utm_content', placement)
    return url.href
  } catch {
    return null
  }
}

const marketPath = /^\/(?:region\d+\/)?[a-z0-9_-]+\/[a-z0-9_-]+\/(?:[a-z0-9_-]+\/)*$/

export function buildDromSearchLinks(searchLink, year, auctionLink) {
  let modelPath = ''
  let wheel = ''
  try {
    const source = new URL(searchLink)
    if (source.origin === 'https://auto.drom.ru' && !source.username && !source.password &&
        marketPath.test(source.pathname)) {
      modelPath = source.pathname
      wheel = source.searchParams.get('w')
    }
  } catch {
    // Иногда оценка Дрома не возвращает ссылку модели.
  }
  if (!modelPath && auctionLink) {
    try {
      const source = new URL(auctionLink)
      if (['https://www.drom.ru', 'https://drom.ru'].includes(source.origin) &&
          !source.username && !source.password) {
        modelPath = /^\/world\/japan(\/[a-z0-9_-]+\/[a-z0-9_-]+\/)$/.exec(source.pathname)?.[1] || ''
      }
    } catch {
      // Общая страница Дрома остаётся доступна.
    }
  }
  const url = new URL(modelPath || '/', 'https://auto.drom.ru')
  if (modelPath && /^\d{4}$/.test(String(year))) {
    url.searchParams.set('minyear', year)
    url.searchParams.set('maxyear', year)
  }
  url.searchParams.set('unsold', '1')
  url.searchParams.set('whereabouts[]', '0')
  if (['1', '2'].includes(wheel)) url.searchParams.set('w', wheel)
  const domestic = url.href
  url.searchParams.set('whereabouts[]', '2')
  url.searchParams.delete('w')
  return { domestic, underOrder: url.href, matchesModel: Boolean(modelPath) }
}

export function orderSearchLabel(links, carTitle) {
  if (!links.matchesModel) return 'Открыть раздел «Под заказ» на Дроме'
  return carTitle ? `Найти ${carTitle} под заказ` : 'Найти автомобиль под заказ'
}
