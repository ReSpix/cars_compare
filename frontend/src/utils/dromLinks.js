export function buildDromSearchLinks(searchLink, { from, to }) {
  if (
    !/^\d{4}$/.test(String(from)) ||
    !/^\d{4}$/.test(String(to)) ||
    Number(from) > Number(to)
  ) {
    return { domestic: null, underOrder: null, invalid: true }
  }
  let basePath = '/'
  try {
    const source = new URL(searchLink)
    if (source.hostname === 'auto.drom.ru' && source.protocol === 'https:') {
      basePath =
        source.pathname.match(/^\/(?:region\d+\/)?[^/]+\/[^/]+\//)?.[0] || '/'
    }
  } catch {
    // Если источник не дал ссылку модели, оставляем общий раздел под заказ.
  }
  const result = new URL(basePath, 'https://auto.drom.ru')
  result.searchParams.set('minyear', from)
  result.searchParams.set('maxyear', to)
  const domestic = basePath === '/' ? null : result.href
  result.searchParams.set('whereabouts[]', '2')
  return { domestic, underOrder: result.href, invalid: false }
}
