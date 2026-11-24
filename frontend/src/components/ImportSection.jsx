import { Fragment } from 'react'
import { Wallet, Percent } from 'lucide-react'
import {
  componentLabel,
  currencySign,
  formatMoney,
  formatNumber,
  formatPriceComponent,
  numericValue,
} from '../utils/format'

const COST_GROUPS = [
  {
    label: 'Пошлина и сборы',
    items: [
      { label: 'Пошлина', names: ['CUSTOMS_DUTY'] },
      { label: 'Таможенный сбор', names: ['CUSTOMS_FEE'] },
      { label: 'Утилизационный сбор', names: ['RECYCLING_FEE'] },
      { label: 'Акциз', names: ['EXCISE_TAX'] },
      { label: 'НДС', names: ['VAT'] },
    ],
  },
  {
    label: 'Доставка и оформление',
    items: [
      { label: 'Расходы по Японии', names: ['SPENDING_ABROAD'] },
      { label: 'Фрахт во Владивосток', names: ['FREIGHT_TO_VLADIVOSTOK'] },
      {
        label: 'Расходы по оформлению в РФ',
        names: ['SPENDING_TO_VLADIVOSTOK', 'REGISTRATION_COSTS'],
      },
      { label: 'Комиссия компании', names: ['COMPANY_COMMISSION'] },
    ],
  },
]

export default function ImportSection({ data }) {
  const total = data?.result?.totalPrice
  const details = data?.result?.details || {}
  const rates = data?.centralBankCurrencyRate?.form || {}

  const rows = Object.entries(details)
    .filter(([, component]) => component != null)
    .map(([name, component]) => ({
      name,
      label: componentLabel(name),
      display: formatPriceComponent(component),
      value: numericValue(component),
    }))

  const rowsByName = new Map(rows.map((row) => [row.name, row]))
  const groupedNames = new Set(
    [
      'PRICE',
      'SPENDING_AND_REGISTRATION',
      'CUSTOMS_DUTY_AND_FEES',
      ...COST_GROUPS.flatMap((group) =>
        group.items.flatMap((item) => item.names),
      ),
    ],
  )
  const groups = COST_GROUPS.map((group) => ({
    ...group,
    itemRows: group.items
      .map((item) => {
        const itemRows = item.names
          .map((name) => rowsByName.get(name))
          .filter(Boolean)
        if (itemRows.length === 0) return null
        return {
          key: item.names.join('-'),
          label: item.label,
          display: itemRows.map((row) => row.display).join(' + '),
        }
      })
      .filter(Boolean),
  })).filter((group) => group.itemRows.length > 0)
  const otherRows = rows.filter((row) => !groupedNames.has(row.name))
  if (otherRows.length > 0) {
    groups.push({
      label: 'Другие расходы',
      itemRows: otherRows,
    })
  }
  const priceRow = rowsByName.get('PRICE')
  const recyclingRow = rowsByName.get('RECYCLING_FEE')
  const customsParts = ['CUSTOMS_DUTY', 'CUSTOMS_FEE']
    .map((name) => rowsByName.get(name))
    .filter((row) => row?.value != null)
  const customsSummary = rowsByName.get('CUSTOMS_DUTY_AND_FEES')
  // The API summary also includes the recycling fee.
  const customsValue =
    customsParts.length > 0
      ? customsParts.reduce((sum, row) => sum + row.value, 0)
      : customsSummary?.value != null
        ? Math.max(customsSummary.value - (recyclingRow?.value || 0), 0)
        : null
  const customsRow =
    customsValue === null
      ? null
      : {
          name: 'customs',
          label: 'Таможня (Пошлина + таможенный сбор)',
          value: customsValue,
        }

  const mainCosts = [
    priceRow && { ...priceRow, label: 'Цена авто в Японии' },
    customsRow,
    recyclingRow && { ...recyclingRow, label: 'Утилизационный сбор' },
    rowsByName.get('SPENDING_AND_REGISTRATION') && {
      ...rowsByName.get('SPENDING_AND_REGISTRATION'),
      label: 'Доставка и оформление',
    },
  ]
    .filter((row) => row?.value != null)
  const totalValue = Number(total?.value)
  const hasTotalValue = Number.isFinite(totalValue) && totalValue > 0

  return (
    <div className="space-y-4">
      {/* Итог + курс */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-gradient-to-br from-brand to-brand-dark rounded-2xl p-6 text-white shadow-lg shadow-brand/20">
          <div className="flex items-center gap-2 mb-3">
            <Wallet className="w-4 h-4 opacity-80" />
            <span className="text-xs uppercase tracking-wider opacity-80 font-semibold">
              Итого «под ключ»
            </span>
          </div>
          <div className="text-4xl font-extrabold tracking-tight">
            {formatMoney(total)}
          </div>
          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm opacity-85">
            <span>
              Цена лота: <strong>{data.form?.price ? `${formatNumber(data.form.price)} ${currencySign(data.form.currency)}` : '—'}</strong>
            </span>
            <span>
              Направление: <strong>{data.importCountry || 'Япония'}</strong>
            </span>
            <span>
              Цель: <strong>{data.form?.importPurpose === 'RESALE' ? 'перепродажа' : 'личное пользование'}</strong>
            </span>
          </div>
        </div>

        <div className="bg-white border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Percent className="w-4 h-4 text-brand" />
            <span className="text-xs uppercase tracking-wider font-semibold text-muted">
              Курс ЦБ РФ
            </span>
          </div>
          <p className="text-xs text-muted mb-3">
            {data.centralBankCurrencyRate?.date || 'Дата не указана'}
          </p>
          <div className="space-y-2">
            {Object.entries(rates).length === 0 && (
              <p className="text-sm text-muted">Курсы не переданы</p>
            )}
            {Object.entries(rates).map(([code, rate]) => (
              <div key={code} className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-semibold text-dark">{code}</span>
                <span className="text-sm text-muted">
                  {formatNumber(rate.value, 4)}
                  {rate.multipliedBy ? ` × ${rate.multipliedBy}` : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Структура затрат */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 bg-white border border-border rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface">
              <tr>
                <th className="text-left px-4 py-2.5 font-semibold text-muted text-xs uppercase tracking-wider">
                  Статья расходов
                </th>
                <th className="text-right px-4 py-2.5 font-semibold text-muted text-xs uppercase tracking-wider">
                  Сумма
                </th>
              </tr>
            </thead>
            <tbody>
              {priceRow && (
                <tr className="border-t border-border">
                  <td className="px-4 py-2.5 font-semibold text-dark">{priceRow.label}</td>
                  <td className="px-4 py-2.5 text-right font-semibold text-dark whitespace-nowrap">
                    {priceRow.display}
                  </td>
                </tr>
              )}
              {groups.map((group) => (
                <Fragment key={group.label}>
                  <tr className="border-t border-border bg-surface/70">
                    <td colSpan={2} className="px-4 py-2 font-semibold text-dark">
                      {group.label}
                    </td>
                  </tr>
                  {group.itemRows.map((row) => (
                    <tr key={row.key || row.name} className="border-t border-border/60">
                      <td className="px-4 py-2 pl-7 text-muted">{row.label}</td>
                      <td className="px-4 py-2 text-right text-dark whitespace-nowrap">
                        {row.display}
                      </td>
                    </tr>
                  ))}
                </Fragment>
              ))}
              {!priceRow && groups.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-4 py-6 text-center text-muted">
                    Детализация не передана
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="lg:col-span-2 bg-white border border-border rounded-2xl p-5">
          <h3 className="text-xs uppercase tracking-wider font-semibold text-muted mb-4">
            Из чего складывается цена
          </h3>
          <div className="space-y-3">
            {(!hasTotalValue || mainCosts.length === 0) && (
              <p className="text-sm text-muted">Нет данных для диаграммы</p>
            )}
            {hasTotalValue && mainCosts.map((row) => (
              <div key={row.name}>
                <div className="flex items-baseline justify-between gap-2 mb-1">
                  <span className="text-xs text-muted truncate">{row.label}</span>
                  <span className="text-xs font-semibold text-dark whitespace-nowrap shrink-0 pl-2">
                    {formatNumber(row.value)}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-surface overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-brand to-accent"
                    style={{
                      width: `${Math.min(Math.max((row.value / totalValue) * 100, 0), 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Параметры запроса к калькулятору */}
      {data.form && (
        <div className="bg-white border border-border rounded-2xl p-5">
          <h3 className="text-xs uppercase tracking-wider font-semibold text-muted mb-3">
            Параметры расчёта
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-4 gap-y-3 text-sm">
            <Param label="Цена" value={data.form.price ? `${formatNumber(data.form.price)} ${currencySign(data.form.currency)}` : '—'} />
            <Param label="Возраст" value={vehicleAgeLabel(data.form.vehicleAge)} />
            <Param label="Двигатель" value={engineTypeLabel(data.form.engineType)} />
            <Param
              label="Объём"
              value={data.form.engineVolumeInCubicCentimeters ? (
                <>
                  <span>
                    {formatNumber(
                      Number(data.form.engineVolumeInCubicCentimeters) / 1000,
                      1,
                    )}{' '}
                    л
                  </span>{' '}
                  <span className="text-muted font-normal">
                    ({formatNumber(data.form.engineVolumeInCubicCentimeters)} см³)
                  </span>
                </>
              ) : '—'}
            />
            <Param
              label="Мощность"
              value={
                data.form.engineHorsePower
                  ? `${formatNumber(data.form.engineHorsePower)} л.с.`
                  : '—'
              }
            />
            <Param
              label="Цель"
              value={importPurposeLabel(data.form.importPurpose)}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function vehicleAgeLabel(value) {
  const labels = {
    UNDER_3: 'до 3 лет',
    FROM_3_TO_5: 'от 3 до 5 лет',
    OVER_5: 'старше 5 лет',
  }
  return labels[value] || value?.replace(/_/g, ' ').toLowerCase()
}

function engineTypeLabel(value) {
  const labels = {
    DIESEL_OR_GASOLINE: 'бензин / дизель',
    ELECTRIC_MOTOR: 'электро',
  }
  return labels[value] || value?.replace(/_/g, ' ').toLowerCase()
}

function importPurposeLabel(value) {
  const labels = {
    USAGE: 'для себя',
    RESALE: 'перепродажа',
  }
  return labels[value] || value?.replace(/_/g, ' ').toLowerCase()
}

function Param({ label, value }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-muted/80">{label}</div>
      <div className="font-semibold text-dark truncate">{value || '—'}</div>
    </div>
  )
}
