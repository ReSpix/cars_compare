export function uniqueOptions(options) {
  return [
    ...new Map(
      options.map((option) => [
        String(option.value),
        {
          ...option,
          value: String(option.value),
          label: String(option.label),
        },
      ]),
    ).values(),
  ]
}

const normalize = (text) =>
  text.trim().toLocaleLowerCase('ru').replaceAll('ё', 'е')

export function filterOptions(options, query) {
  const needle = normalize(query)
  if (!needle) return options
  const prefix = []
  const other = []
  for (const option of options) {
    const label = normalize(option.label)
    if (label.startsWith(needle)) prefix.push(option)
    else if (label.includes(needle)) other.push(option)
  }
  return [...prefix, ...other]
}
