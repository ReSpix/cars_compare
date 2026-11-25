import { useState } from 'react'
import { GitCompareArrows } from 'lucide-react'
import clsx from 'clsx'
import {
  getFirms,
  getModels,
  getYears,
  getFrames,
  getGenerations,
  getModifications,
  getRegions,
} from '../services/api'
import { FRAME_LABELS, WHEEL_OPTIONS } from '../constants/catalog'
import useCatalog from '../hooks/useCatalog'
import SearchableSelect from './SearchableSelect'

const defaults = {
  regionId: '0',
  firmId: '',
  modelId: '',
  wheel: '',
  year: '',
  frame: '',
  generationId: '',
  modificationId: '',
}
const cascade = [
  'firmId',
  'modelId',
  'wheel',
  'year',
  'frame',
  'generationId',
  'modificationId',
]

export default function CarSearchForm({
  onSubmit,
  disabled = false,
  initialSelection = {},
}) {
  const [selection, setSelection] = useState(() =>
    Object.fromEntries(
      Object.entries(defaults).map(([key, value]) => [
        key,
        String(initialSelection[key] ?? value),
      ]),
    ),
  )
  const {
    regionId,
    firmId,
    modelId,
    wheel,
    year,
    frame,
    generationId,
    modificationId,
  } = selection
  const regions = useCatalog(getRegions, 'regions')
  const firms = useCatalog(getFirms, 'firms')
  const models = useCatalog(
    () => getModels(firmId, Number(regionId)),
    `${firmId}:${regionId}`,
    !!firmId,
  )
  const years = useCatalog(
    () => getYears(modelId, wheel),
    `${modelId}:${wheel}`,
    !!modelId && !!wheel,
  )
  const frames = useCatalog(
    () => getFrames(modelId, year, wheel),
    `${modelId}:${year}:${wheel}`,
    !!modelId && !!year && !!wheel,
  )
  const generations = useCatalog(
    () => getGenerations(modelId, year, frame, wheel),
    `${modelId}:${year}:${frame}:${wheel}`,
    !!frame && !!year && !!modelId && !!wheel,
  )
  const modifications = useCatalog(
    () => getModifications(modelId, year, frame, generationId, wheel),
    `${modelId}:${year}:${frame}:${generationId}:${wheel}`,
    !!generationId && !!frame && !!year && !!modelId && !!wheel,
  )
  const chosenModel = models.items.find((model) => String(model.id) === modelId)
  const wheels = WHEEL_OPTIONS.filter((option) =>
    chosenModel?.wheels.includes(option.value),
  )

  const change = (field, value) => {
    setSelection((previous) => {
      const next = { ...previous, [field]: value }
      const index = field === 'regionId' ? 0 : cascade.indexOf(field)
      cascade.slice(index + 1).forEach((key) => {
        next[key] = defaults[key]
      })
      if (field === 'modelId') {
        const available =
          models.items.find((model) => String(model.id) === value)?.wheels ?? []
        next.wheel = available.includes(previous.wheel)
          ? previous.wheel
          : (available[0] ?? '')
      }
      return next
    })
  }
  const catalogs = [
    regions,
    firms,
    models,
    years,
    frames,
    generations,
    modifications,
  ]
  const isReady =
    cascade.every((key) => selection[key]) &&
    !catalogs.some((catalog) => catalog.loading || catalog.error)
  const fields = [
    {
      key: 'regionId',
      label: 'Регион',
      catalog: regions,
      options: regions.items.map((item) => ({
        value: item.code,
        label: item.name,
      })),
      placeholder: 'Выберите регион',
    },
    {
      key: 'firmId',
      label: 'Марка',
      catalog: firms,
      options: firms.items.map((item) => ({
        value: item.id,
        label: item.title,
      })),
      placeholder: 'Начните вводить марку',
    },
    {
      key: 'modelId',
      label: 'Модель',
      catalog: models,
      options: models.items.map((item) => ({
        value: item.id,
        label: item.title,
      })),
      blocked: !firmId,
    },
    {
      key: 'wheel',
      label: 'Руль',
      options: wheels,
      blocked: !modelId || models.loading,
    },
    {
      key: 'year',
      label: 'Год для расчёта',
      catalog: years,
      options: years.items.map((item) => ({ value: item, label: item })),
      blocked: !modelId || !wheel,
    },
    {
      key: 'frame',
      label: 'Кузов',
      catalog: frames,
      options: frames.items.map((item) => ({
        value: item,
        label: FRAME_LABELS[item] || item,
      })),
      blocked: !year,
    },
    {
      key: 'generationId',
      label: 'Поколение',
      catalog: generations,
      options: generations.items.map((item) => ({
        value: item.id,
        label: item.title,
      })),
      blocked: !frame,
    },
    {
      key: 'modificationId',
      label: 'Модификация',
      catalog: modifications,
      options: modifications.items.map((item) => ({
        value: item.id,
        label: item.title,
      })),
      blocked: !generationId,
    },
  ]
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (!isReady || disabled) return
        onSubmit?.({
          ...selection,
          firm: firms.items.find((item) => String(item.id) === firmId),
          model: chosenModel,
          generation: generations.items.find(
            (item) => String(item.id) === generationId,
          ),
          modification: modifications.items.find(
            (item) => String(item.id) === modificationId,
          ),
          region: regions.items.find((item) => String(item.code) === regionId),
        })
      }}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {fields.map((field) => (
          <SearchableSelect
            key={field.key}
            label={field.label}
            value={selection[field.key]}
            options={field.options}
            onChange={(value) => change(field.key, value)}
            disabled={disabled || field.blocked}
            loading={field.catalog?.loading}
            error={field.catalog?.error}
            onRetry={field.catalog?.retry}
            placeholder={
              field.placeholder ??
              `Выберите ${field.label.toLocaleLowerCase('ru')}`
            }
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button
          type="submit"
          disabled={!isReady || disabled}
          className={clsx(
            'inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold transition-all',
            isReady && !disabled
              ? 'bg-brand text-white shadow-lg shadow-brand/25 hover:bg-brand-dark'
              : 'cursor-not-allowed bg-border text-muted',
          )}
        >
          <GitCompareArrows className="h-4 w-4" />
          Построить отчёт
        </button>
        <p className="text-sm leading-6 text-muted">
          Расчёт — для одного года и модификации. Диапазон поиска можно задать в
          отчёте.
        </p>
      </div>
    </form>
  )
}
