import { formatNumber } from '../utils/format'
import VehicleCard from './VehicleCard'

export default function SimilarCarCard({ bull, title }) {
  const details = [bull.location, bull.mileage == null ? null : `${formatNumber(bull.mileage)} км`].filter(Boolean)
  return (
    <VehicleCard
      title={title || 'Автомобиль в России'} image={bull.src2x || bull.src}
      price={formatNumber(bull.price) ? `${formatNumber(bull.price)} ₽` : 'Цена не указана'}
      source="Объявление в России" details={details} href={bull.url}
      placement="russia_listing" linkLabel="Смотреть объявление на Дроме"
    />
  )
}
