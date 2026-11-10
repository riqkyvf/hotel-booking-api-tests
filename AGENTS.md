# Автотесты Hotel Booking API

Этот репозиторий содержит интеграционные тесты отдельного приложения `hotel-booking-api`. В CI используется Python 3.14.2. Версии pytest, requests, psycopg, jsonschema и Allure закреплены в [requirements.txt](requirements.txt).

## Где вносить изменения

- `tests/` — сценарии по областям `auth`, `users`, `hotels`, `rooms`, `bookings`, `payments` и проверки health. Сценарии на стыке областей размещай рядом с тестами основного проверяемого правила.
- `tests/conftest.py` — общие фикстуры пользователей, токенов, номеров, броней и платежей. Фикстуры одного модуля держи рядом с его тестами. Используй собственные тестовые сущности и параметризуй однотипные варианты.
- `api/` — функции HTTP-запросов на requests. Проверки результата оставляй в сценариях. Переиспользуй `assert_api_error` из `tests/assertions.py` для общего контракта ошибок. Наборы входных данных лежат в `data/`, JSON Schema ответов — в `schemas/`.
- `db.py` — подготовка дат конкретных тестовых броней и чтение состояния и истории. Переходы состояний выполняет приложение. После успешной операции проверяй сохранённое состояние, после отказа — отсутствие нежелательных изменений. [Работа с PostgreSQL](docs/database-schema.md)

## Стенд и команды

Команды ниже выполняются из корня автотестов в PowerShell. Локальный API с PostgreSQL поднимается через `docker compose up --build --wait` из каталога приложения. Нужен Docker Desktop в режиме Linux containers. Перед прогоном проверь `/api/v1/health/ready`. [Подготовка стенда](docs/README.md#запуск-отдельного-приложения)

Используй выделенный тестовый стенд. Тесты создают и меняют записи, локальной общей очистки нет. Шаблон настроек — `.env.example`. Переменные окружения имеют приоритет над `.env`. `API_BASE_URL` по умолчанию указывает на `http://localhost:8000/api/v1`. Для подготовки отелей и номеров нужны `API_ADMIN_EMAIL` и `API_ADMIN_PASSWORD` активного администратора. Для тестов с меткой `db` укажи `TEST_DATABASE_URL` той же базы PostgreSQL, которую использует API. Храни `.env` локально.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

| Набор | Команда |
| --- | --- |
| Smoke | `.\.venv\Scripts\python.exe -m pytest -m smoke -q` |
| Одна область, например бронирования | `.\.venv\Scripts\python.exe -m pytest tests/bookings/ -q` |
| Основная фаза полного прогона | `.\.venv\Scripts\python.exe -m pytest -m 'not isolated_admin' -q --tb=short --durations=15 --junitxml=junit-full.xml` |
| Финальная фаза полного прогона | `.\.venv\Scripts\python.exe scripts/run_last_admin_tests.py` |

Проверки `isolated_admin` меняют роли при подготовке данных. Локально запускай их скриптом на временном стенде. Скрипту нужен собранный образ `hotel-booking-api`. В CI флаг `--reuse-ci-stand` используется только в финальной фазе `full` на одноразовом стенде. [Условия изолированного запуска](docs/testing-auth.md#отдельный-запуск-защиты-последнего-admin)

## Контракт и CI

- Ожидаемое поведение сверяй с требованиями и REST-спецификацией приложения. Ссылки и карта покрытия собраны в [docs/README.md](docs/README.md#контракт). Учитывай версию проверяемого API. Документация в `main` приложения может опережать коммит, закреплённый в CI. Известное расхождение OpenAPI и поведения при `null` в профиле описано в [docs/testing-auth.md](docs/testing-auth.md#profile-checklist).
- [Workflow API tests](.github/workflows/api-tests.yml) запускает smoke для PR в `main` и push в `main`. Ручной запуск поддерживает `smoke` и `full`. Для диагностики используй Allure, JUnit и логи Compose из артефакта запуска. [Локальный отчёт Allure](docs/README.md#локальный-отчёт-allure)
