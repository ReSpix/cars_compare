import VehicleCard from './VehicleCard'
import { formatNumber } from '../utils/format'

export default function AuctionCard({ car }) {
  const details = []
  if (car.auction_date) details.push(`Аукцион ${new Date(`${car.auction_date}T00:00:00`).toLocaleDateString('ru-RU')}`)
  if (car.productionDate) details.push(`${car.productionDate} г.`)
  if (car.engine_volume) details.push(`${(car.engine_volume / 1000).toFixed(1)} л`)
  if (car.mileage != null) details.push(`${formatNumber(car.mileage)} км`)
  if (car.rating != null) details.push(`Оценка ${car.rating.toFixed(1)}`)
  return (
    <VehicleCard
      title={car.name || 'Автомобиль с аукциона'} image={car.image_url}
      price={car.price_jpy ? `¥${formatNumber(car.price_jpy)}` : 'Цена не указана'}
      source="Аукцион Японии" details={details} href={car.url}
      placement="auction_lot" linkLabel="Смотреть лот на Дроме"
    />
  )
}
