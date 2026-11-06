# Автотесты Hotel Booking API

[![API tests](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml/badge.svg?branch=main)](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml)

Автотесты для [Hotel Booking API](https://github.com/riqkyvf/hotel-booking-api) на **Python, pytest и requests**. Набор проверяет 29 операций: регистрацию и права доступа, отели и номера, доступность, бронирования, платежи и health. Сценарии охватывают конкуренцию, повторы с `Idempotency-Key` и переходы состояний с проверкой в PostgreSQL.

[Запуски CI и артефакты Allure](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml) · [Карта покрытия](docs/README.md#карта-покрытия-api) · [Состав smoke](docs/README.md#smoke-suite)

## Быстрый старт

1. Поднимите локальный API с PostgreSQL через Docker Compose и дождитесь `GET /api/v1/health/ready`. [Запуск стенда](docs/README.md#запуск-отдельного-приложения)
2. Из корня репозитория автотестов создайте окружение Python 3.14.2 и запустите 19 smoke-проверок. Копируйте `.env.example`, если `.env` ещё нет.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pytest -m smoke -q
```

| Переменная | Для чего нужна |
| --- | --- |
| `API_BASE_URL` | Адрес API. По умолчанию `http://localhost:8000/api/v1` |
| `API_ADMIN_EMAIL`, `API_ADMIN_PASSWORD` | Активный администратор для подготовки отелей и номеров |
| `TEST_DATABASE_URL` | PostgreSQL DSN той же тестовой БД для тестов с меткой `db` |

Значения окружения имеют приоритет над `.env`. Для воспроизводимого полного прогона используйте отдельный стенд со свежей БД, как в CI. Во время прогона избегайте параллельных изменений данных: тест пагинации пользователей сравнивает несколько страниц общего списка.

Основная регрессия и проверки последнего администратора локально:

```powershell
.\.venv\Scripts\python.exe -m pytest -m 'not isolated_admin' -q --tb=short --durations=15 --junitxml=junit-full.xml
.\.venv\Scripts\python.exe scripts/run_last_admin_tests.py
```

Вторая команда создаёт временный локальный стенд. [Условия запуска](docs/testing-auth.md#отдельный-запуск-защиты-последнего-admin)

## GitHub Actions и Allure

[API tests](.github/workflows/api-tests.yml) запускает smoke на pull request в `main` и при каждом `push` в `main`. Для ручного запуска откройте **Actions → API tests → Run workflow** и выберите `smoke` или `full`. Режим `full` включает DB-тесты. После основной регрессии отдельный шаг **Test last active administrator** оставляет одного активного администратора на том же временном стенде и запускает три проверки `isolated_admin`.

Каждый запуск скачивает приложение по коммиту, указанному в шаге **Check out API**. Compose поднимает отдельный PostgreSQL, выполняет миграции и seed, запускает API и worker. Workflow ждёт готовности стенда и удаляет его том после прогона. Пароли и ключ подписи генерируются для этого стенда, поэтому настройки секретов репозитория не требуются.

На вкладке **Summary** видны результаты и время каждой фазы, коммиты API и тестов и ссылка на артефакт. В завершённом запуске скачайте артефакт `api-tests-smoke` или `api-tests-full` и откройте `allure-report/index.html` из распакованного архива. Рядом лежат `junit.xml` и `compose.log`. В режиме `full` Allure объединяет обе фазы, а `junit-last-admin.xml` содержит отдельный результат второй фазы. Отчёт и JUnit сохраняются после падений тестов, если pytest успел записать результаты. При сбое запуска стенда для диагностики служит `compose.log`. Артефакты хранятся 14 дней.

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
