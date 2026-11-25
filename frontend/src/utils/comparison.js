const positive = (value) => Number.isFinite(Number(value)) && Number(value) > 0

export function getDomesticPrice(report) {
  const estimate = report?.price_change_chart?.recommendedPrice
  if (positive(estimate))
    return {
      value: Number(estimate),
      source: 'drom_estimate',
      sampleCount: null,
    }
  const listings = new Map()
  for (const bull of report?.similar_cars?.bulls || []) {
    if (bull.url && positive(bull.price))
      listings.set(bull.url, Number(bull.price))
  }
  const prices = [...listings.values()]
  return prices.length
    ? {
        value: Math.round(
          prices.reduce((sum, price) => sum + price, 0) / prices.length,
        ),
        source: 'listing_average',
        sampleCount: prices.length,
      }
    : { value: null, source: null, sampleCount: 0 }
}

export function getImportRestrictions(report, selection) {
  const title = selection.modificationTitle || ''
  const reportedVolume =
    report?.japan_import_response?.form?.engineVolumeInCubicCentimeters ??
    report?.query?.engine_volume
  const match = title.match(/^\s*(\d+(?:[.,]\d+)?)\s*л(?:\.?)(?=\s*,)/i)
  const volume = positive(reportedVolume)
    ? Number(reportedVolume)
    : match
      ? Number(match[1].replace(',', '.')) * 1000
      : 0
  const reasons = []
  if (volume > 1900)
    reasons.push(
      `Двигатель ${(volume / 1000).toLocaleString('ru-RU')} л — объём более 1,9 л`,
    )
  if (/гибрид|hybrid|\bPHEV\b|\bHEV\b/i.test(title))
    reasons.push(
      'Гибрид: ограничения Японии на экспорт в Россию распространяются и на двигатели до 1,9 л',
    )
  if (
    /электр|electric|\bBEV\b|\bEV\b/i.test(title) ||
    report?.query?.engine_type === 'ELECTRIC_MOTOR'
  )
    reasons.push('Электрический автомобиль')
  const price =
    selection.price ||
    report?.japan_import_response?.form?.price ||
    report?.query?.price ||
    report?.auctions?.avg_price_jpy
  if (Number(price) > 6_000_000)
    reasons.push(
      'Расчётная цена автомобиля выше 6 млн иен — требуется проверка стоимости конкретного лота',
    )
  if (
    [
      'TRUCK',
      'BOX_TRUCK',
      'CHASSIS_CAB',
      'TRUCK_TRACTOR',
      'BUS',
      'VAN',
      'PICKUP',
    ].includes(selection.frame)
  )
    reasons.push('Нужна проверка экспортной категории коммерческого автомобиля')
  return reasons
}

export function getComparisonConclusion(report, selection) {
  const restrictions = getImportRestrictions(report, selection)
  if (restrictions.length)
    return {
      kind: 'restricted',
      title: 'Проверьте условия экспорта из Японии',
      restrictions,
      description:
        'Для этой модификации возможны ограничения на прямой экспорт из Японии. Если потребуется другой маршрут, привоз может занять больше времени и обойтись дороже.',
    }
  const domestic = getDomesticPrice(report).value
  const importMoney = report?.japan_import_response?.result?.totalPrice
  const imported = Number(importMoney?.value)
  if (
    domestic === null ||
    !positive(imported) ||
    importMoney?.currency !== 'RUB'
  )
    return {
      kind: 'incomplete',
      title: 'Пока недостаточно данных для сравнения',
      description:
        domestic === null
          ? 'Оценка для России пока недоступна. Можно посмотреть цены в объявлениях по выбранной модели.'
          : 'Цена в России уже есть. Для расчёта привоза можно указать цену конкретного лота в иенах и пересчитать отчёт.',
    }
  const difference = Math.abs(domestic - imported)
  const percent = (difference / domestic) * 100
  if (percent <= 5)
    return {
      kind: 'close',
      title: 'Стоимость вариантов сопоставима',
      difference,
      percent,
      description:
        'При такой разнице важнее, как скоро вам нужна машина и хотите ли вы осмотреть её до покупки. Если рассматриваете заказ, прибавьте к расчёту доставку от Владивостока до вашего города.',
    }
  return domestic > imported
    ? {
        kind: 'japan',
        title: 'Привезти из Японии дешевле по расчёту',
        difference,
        percent,
        description:
          'От покупки на аукционе до выдачи во Владивостоке ориентируйтесь на 30–45 дней. Подбор машины до покупки может занять от нескольких дней до трёх недель.',
        note: 'Итоговая стоимость зависит от цены конкретного лота, курса оплаты и доставки до вашего города.',
      }
    : {
        kind: 'russia',
        title: 'Купить в России дешевле по расчёту',
        difference,
        percent,
        description:
          'Если машина есть в наличии, её можно осмотреть и купить без ожидания доставки из Японии. Сравните пробег и состояние конкретных машин в объявлениях, прежде чем выбирать по цене.',
      }
}
