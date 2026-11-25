# Развёртывание АвтоСчёта

На VPS с Ubuntu 24.04 нужны Docker Engine и Docker Compose V2 с поддержкой `!reset` (Compose 2.24.4 или новее). Домен должен указывать на публичный IP VPS. Порты 80 и 443 должны быть доступны извне. Подключайтесь по SSH отдельной учётной записью с ключом.

Скопируйте исходники релиза на VPS и создайте конфигурацию.

```sh
cp deploy/production.env.example deploy/production.env
docker compose -p avto-summa --env-file deploy/production.env -f compose.yaml -f compose.production.yaml config -q
docker compose -p avto-summa --env-file deploy/production.env -f compose.yaml -f compose.production.yaml up -d --build --wait
docker compose -p avto-summa --env-file deploy/production.env -f compose.yaml -f compose.production.yaml logs --tail 50 api caddy
```

Проверьте, что `https://avto-summa.online/health` отвечает по HTTPS. Откройте приложение, посчитайте одну модель с введённым бюджетом и запустите подбор, если оба варианта превышают бюджет. Проверьте с VPS доступ к сервисам Дрома.

## Обновление и откат

Храните исходники предыдущего релиза вместе с его конфигурацией. Запускайте каждый релиз с одним и тем же именем проекта `-p avto-summa`, чтобы использовать сохранённые тома. Для обновления или отката выполните команды проверки и запуска из папки выбранного релиза. Данные SQLite и состояние HTTPS находятся в томах Compose. Для отката с несовместимой миграцией требуется восстановить резервную копию базы. В этом релизе добавляются только таблица кеша и колонка времени логов.

## Метрика

Создайте счётчик для домена и укажите его номер в `VITE_METRIKA_COUNTER_ID` в файле `deploy/production.env`. Пересоберите фронтенд тем же запуском Compose. Счётчик по умолчанию выключен и не отправляет события на localhost. В панели Метрики создайте цели типа «JavaScript-событие» с именами `comparison_requested`, `comparison_completed`, `alternatives_requested`, `alternatives_completed` и `drom_outbound`. Проверьте их на опубликованном сайте. Параметр `placement` у перехода показывает место ссылки. UTM-метки в адресе Дрома дополняют данные на стороне сервиса-получателя.
