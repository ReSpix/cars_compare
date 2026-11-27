import { Car } from 'lucide-react'
import DromLink from './DromLink'

const YEAR = new Date().getFullYear()

export default function Footer() {
  return (
    <footer className="bg-darker text-white/70 mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center">
                <Car className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-extrabold text-white">
                Авто<span className="text-brand">Сумма</span>
              </span>
            </div>
            <p className="text-sm leading-relaxed">
              Сравнение цен в России и стоимости привоза из Японии.
            </p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3 text-sm uppercase tracking-wider">
              В отчёте
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <DromLink
                  href="https://auto.drom.ru/rate_car/"
                  placement="footer_estimate"
                  className="text-white/70 hover:text-white transition-colors"
                >
                  Рекомендованная цена
                </DromLink>
              </li>
              <li>
                <DromLink
                  href="https://www.drom.ru/world/japan/"
                  placement="footer_auctions"
                  className="text-white/70 hover:text-white transition-colors"
                >
                  Лоты японских аукционов
                </DromLink>
              </li>
              <li>
                <DromLink
                  href="https://www.drom.ru/world/calculator/japan/"
                  placement="footer_calculator"
                  className="text-white/70 hover:text-white transition-colors"
                >
                  Калькулятор стоимости привоза
                </DromLink>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 mt-8 pt-6 text-center text-xs">
          © {YEAR} АвтоСумма. Данные предоставлены сервисами Drom.ru.
        </div>
      </div>
    </footer>
  )
}
