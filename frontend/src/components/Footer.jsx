import { Car } from 'lucide-react'

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
                Авто<span className="text-brand">Срав</span>
              </span>
            </div>
            <p className="text-sm leading-relaxed">
              Один отчёт вместо десяти вкладок: рыночная оценка, аукционы Японии,
              похожие объявления и полная стоимость импорта под ключ.
            </p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3 text-sm uppercase tracking-wider">
              В отчёте
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="https://auto.drom.ru/rate_car/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white/70 hover:text-white transition-colors"
                >
                  Рекомендованная цена
                </a>
              </li>
              <li>
                <a
                  href="https://www.drom.ru/world/japan/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white/70 hover:text-white transition-colors"
                >
                  Лоты японских аукционов
                </a>
              </li>
              <li>
                <a
                  href="https://www.drom.ru/world/calculator/japan/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white/70 hover:text-white transition-colors"
                >
                  Калькулятор стоимости привоза
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 mt-8 pt-6 text-center text-xs">
          © {YEAR} АвтоСчет. Данные предоставлены сервисами Drom.ru.
        </div>
      </div>
    </footer>
  )
}
