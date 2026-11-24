# Веб-интерфейс

React-приложение на Vite. В production Docker-образ собирает статические файлы и отдаёт их через Nginx; запросы к API Nginx направляет сервису `api`.

Запускайте приложение из корня `cars_compare`:

```powershell
docker compose up --build
```

Интерфейс будет доступен на порту `8080`. Для разработки используйте
`docker compose -f compose.yaml -f compose.dev.yaml up --build`; Vite будет
доступен на порту `5173`.
