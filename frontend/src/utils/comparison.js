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
        'Предупреждение относится к экспорту из Японии в Россию. Оно не означает запрет на покупку такого автомобиля в России. Расчёт привоза не подтверждает доступность поставки и не учитывает возможные дополнительные расходы. Возможность поставки, стоимость и сроки нужно подтвердить у поставщика.',
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
          ? 'Не удалось получить российскую оценку. Без неё нельзя определить более выгодный вариант.'
          : 'Нет полного расчёта привоза. Попробуйте другую модификацию или укажите цену конкретного лота. Отсутствие найденных лотов не означает запрет на поставку.',
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
        'Разница не превышает 5%. Её могут перекрыть доставка до вашего города, курс оплаты и состояние автомобиля. Учитывайте сроки и возможность осмотра перед покупкой.',
    }
  return domestic > imported
    ? {
        kind: 'japan',
        title: 'Привоз до Владивостока дешевле по расчёту',
        difference,
        percent,
        description:
          'Потребуется время на подбор, покупку, доставку и оформление. Итог зависит от конкретного лота, курса оплаты и доставки до вашего города. Сроки уточните у поставщика.',
      }
    : {
        kind: 'russia',
        title: 'Покупка в России дешевле по расчёту',
        difference,
        percent,
        description:
          'Можно рассматривать автомобили в наличии, осмотреть их перед покупкой и обойтись без ожидания международной доставки. Проверьте состояние, документы и фактическое наличие выбранной машины.',
      }
}
