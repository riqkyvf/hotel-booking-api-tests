# Автотесты Hotel Booking API

[![API tests](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml/badge.svg?branch=main)](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml)

Автотесты для [Hotel Booking API](https://github.com/riqkyvf/hotel-booking-api) на **Python, pytest и requests**. Набор проверяет 29 операций: регистрацию и права доступа, отели и номера, доступность, бронирования, платежи и health. Сценарии охватывают конкуренцию, повторы с `Idempotency-Key` и переходы состояний с проверкой в PostgreSQL.

[Запуски CI и артефакты Allure](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml) · [Карта покрытия](docs/README.md#карта-покрытия-api) · [Состав smoke](docs/README.md#smoke-suite)

## Быстрый старт

1. Поднимите локальный API с PostgreSQL через Docker Compose и дождитесь `GET /api/v1/health/ready`. [Запуск стенда](docs/README.md#запуск-отдельного-приложения)
2. Из корня репозитория автотестов выполните команды ниже с Python 3.14.2. Они установят зависимости, создадут локальный `.env` из шаблона [`.env.example`](.env.example) и запустят 19 smoke-проверок. Готовый `.env` хранится только на вашей машине. Если файл уже есть, команда сохранит ваши настройки.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pytest -m smoke -q
```

Для стенда с другими настройками измените значения в `.env`.

| Переменная | Для чего нужна |
| --- | --- |
| `API_BASE_URL` | Адрес API. По умолчанию `http://localhost:8000/api/v1` |
| `API_ADMIN_EMAIL`, `API_ADMIN_PASSWORD` | Активный администратор для подготовки отелей и номеров |
| `TEST_DATABASE_URL` | Строка подключения к той же базе PostgreSQL, которую использует API. Нужна для тестов с меткой `db` |

Для полного локального прогона на тестовом стенде выполните обе команды.

```powershell
.\.venv\Scripts\python.exe -m pytest -m 'not isolated_admin' -q --tb=short --durations=15 --junitxml=junit-full.xml
.\.venv\Scripts\python.exe scripts/run_last_admin_tests.py
```

Вторая команда создаёт временный локальный стенд. [Условия запуска](docs/testing-auth.md#отдельный-запуск-защиты-последнего-admin)

## GitHub Actions и Allure

[API tests](.github/workflows/api-tests.yml) запускает smoke на pull request в `main` и при каждом `push` в `main`. Для ручного запуска откройте **Actions → API tests → Run workflow** и выберите `smoke` или `full`. Режим `full` включает DB-тесты. После основной регрессии отдельный шаг **Test last active administrator** оставляет одного активного администратора на том же временном стенде и запускает три проверки `isolated_admin`.

CI поднимает временный стенд с версией приложения из шага **Check out API**. Учётные данные генерируются при запуске.

На вкладке **Summary** видны результаты, время каждой фазы, версии API и тестов и ссылка на артефакт. Скачайте архив запуска и откройте `allure-report/index.html`. В режиме `full` Allure объединяет обе фазы. Для диагностики в архиве также есть JUnit и логи Compose.

Для локального Allure-отчёта установите зависимости из `requirements.txt`. С запущенным стендом выполните smoke и сгенерируйте HTML. Для второй команды нужны Node.js и Java.

```powershell
.\.venv\Scripts\python.exe -m pytest -m smoke -q --alluredir=artifacts/allure-results --clean-alluredir
npm.cmd exec --yes --package=allure-commandline@2.46.1 -- allure generate artifacts/allure-results --output artifacts/allure-report --single-file --clean
```

Откройте `artifacts/allure-report/index.html` в браузере. Папка `artifacts/` исключена из Git.

## Структура проекта

| Путь | Назначение |
| --- | --- |
| `tests/` | Сценарии, фикстуры, общая проверка ошибок |
| `api/` | Функции HTTP-запросов на requests |
| `data/`, `schemas/` | Наборы параметров и JSON Schema ответов |
| `db.py` | SQL-подготовка дат и чтение истории состояний |
| `scripts/` | Запуск проверок последнего администратора и формирование сводки CI |
| `docs/` | Контракт, карта покрытия и сценарии |
