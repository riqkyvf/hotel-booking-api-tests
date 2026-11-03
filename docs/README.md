# Документация и эксплуатация

Основная инструкция запуска тестов: [README проекта](../README.md).

## Запуск отдельного приложения

Приложение находится в отдельном репозитории [Hotel Booking API](https://github.com/riqkyvf/hotel-booking-api). В репозитории автотестов нет `compose.yaml`, Dockerfile и исходников приложения. Нужен запущенный Docker Desktop с Linux containers.

Из каталога, где вы храните проекты, выполните:

```powershell
git clone https://github.com/riqkyvf/hotel-booking-api.git
Set-Location hotel-booking-api
docker compose up --build -d
docker compose ps -a
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
git rev-parse HEAD
```

Если приложение уже клонировано, перейдите в его каталог с `compose.yaml` и запускайте команды оттуда. Дождитесь HTTP 200 и `status = ready`; если init ещё работает, повторите проверку после его завершения. Сохраните commit приложения вместе с результатом прогона. Исторический commit приложения для результата от 01.11.2026 не был зафиксирован; совместимость новой версии подтверждается отдельным прогоном.

После подготовки стенда вернитесь в каталог автотестов и следуйте основному README. `.env` приложения и `.env` автотестов — разные файлы: первый настраивает сервер, второй — адрес API и учётные данные для тестов. Для локального запуска приложение имеет свои демонстрационные настройки по умолчанию.

Нормативные документы:

- [requirements.md](requirements.md) — функции, границы, идемпотентность, истечение, деактивация, платежи и конкурентные операции.
- [api-specification.md](api-specification.md) — 29 операций, параметры, авторизация, примеры, HTTP-коды и формат ошибок.
- [business-rules.md](business-rules.md) — стоимость, доступность и граф состояний.
- [database-schema.md](database-schema.md) — поля, типы, связи и ограничения.

## Адреса

Swagger: [localhost:8000/docs](http://localhost:8000/docs). OpenAPI: [localhost:8000/openapi.json](http://localhost:8000/openapi.json). Readiness: [localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready).

## Локальная БД / DBeaver

Драйвер PostgreSQL; host `localhost`, port `5433`, database `hotel`, user `hotel`, password `hotel_dev_password`, SSL disabled. Это демонстрационные локальные настройки приложения. При изменении `.env` приложения используйте свои значения. JDBC URL: `jdbc:postgresql://localhost:5433/hotel`. Схема `public`. Для времён UTC выполните `SET TIME ZONE 'UTC'` в нужной SQL-сессии.

## Seed и сброс

Учётные записи: admin@example.com, admin2@example.com, alice@example.com, bob@example.com, disabled@example.com. Общий локальный пароль `HotelDemo123!`; последняя учётная запись неактивна. При первом старте seed выполняется автоматически, повторный запуск не изменяет данные.

Сброс без публичного HTTP-эндпоинта; владелец отдельного тестового стенда выполняет команды из корня **репозитория приложения**, где лежит `compose.yaml`. Команды удаляют все данные приложения; во время сброса тесты и другие пользователи стенда работать не должны:

```powershell
docker compose stop api worker
docker compose run --rm --no-deps api python -m app.scripts.reset_db --confirm-reset
docker compose up -d
```

## Диагностика

Все Docker-команды выполняются в репозитории приложения. `docker compose ps -a` показывает `db/api/worker` healthy и `init` exited (0). При проблемах используйте `docker compose logs --tail 100 init api worker db`. Проверка миграции: `docker compose exec api alembic current`, сверка моделей: `docker compose exec api alembic check`.

Worker повторяет проход через 5 секунд; healthcheck считает его готовым, если успешный проход был менее 60 секунд назад. Ошибки пишутся в stdout/stderr контейнеров. API возвращает request_id для сопоставления ошибок с журналом; секреты не включаются в ответы об ошибках.

Неоплаченные seed-брони меняют состояние со временем — это нормальное поведение. Точность проверки срока не зависит от частоты worker: API сверяет `clock_timestamp()` после получения блокировок.
