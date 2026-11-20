# Запуск и отчёты

Команды рассчитаны на PowerShell. Нужны Git, Python 3.14.2 и Docker Desktop в режиме Linux containers. Версии Python-зависимостей закреплены в [requirements.txt](../requirements.txt).

## Подготовка стенда

Используйте выделенный тестовый стенд. Тесты изменяют данные, которые остаются в локальной базе после прогона. Compose по умолчанию использует имя `hotel-booking`, поэтому запуск из другой папки с тем же именем проекта использует тот же том PostgreSQL. Для параллельного стенда задайте отдельное имя Compose-проекта и свободные порты.

Команды ниже поднимают версию API из [CI](../.github/workflows/api-tests.yml). Выполните их из каталога, где хранятся проекты.

```powershell
git clone https://github.com/riqkyvf/hotel-booking-api.git
Set-Location hotel-booking-api
git checkout 0d8396f38c8a7b727648585e33b3d34fe54652ab
docker compose up --build --wait
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

Ожидается `status: ready`. Если изменили порт API, используйте его и для запроса readiness.

В другом окне PowerShell клонируйте автотесты:

```powershell
git clone https://github.com/riqkyvf/hotel-booking-api-tests.git
Set-Location hotel-booking-api-tests
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Если репозиторий уже клонирован, начните с `python -m venv .venv` из его корня. Если `.env` уже есть, пропустите копирование. Значения в [шаблоне](../.env.example) соответствуют стандартным настройкам Compose. Укажите в `.env` свои порты и учётные данные, если меняли их в Compose. Переменные окружения имеют приоритет над `.env`.

| Переменная | Назначение |
| --- | --- |
| `API_BASE_URL` | Адрес API с префиксом `/api/v1`; по умолчанию `http://localhost:8000/api/v1` |
| `API_ADMIN_EMAIL`, `API_ADMIN_PASSWORD` | Активный admin для подготовки отелей и номеров |
| `TEST_DATABASE_URL` | PostgreSQL той же тестовой базы, которую использует API; нужен для `db`-тестов |
| `JWT_SECRET` | Ключ подписи выделенного тестового API. Нужен для проверки истечения JWT в `full`. В CI задаётся автоматически |

## Наборы и полный прогон

Все команды ниже выполняются из корня автотестов.

| Набор | Команда |
| --- | --- |
| Smoke | `.\.venv\Scripts\python.exe -m pytest -m smoke -q` |
| Одна область | `.\.venv\Scripts\python.exe -m pytest tests/bookings/ -q` |
| Основная фаза полного прогона | `.\.venv\Scripts\python.exe -m pytest -m 'not isolated_admin' -q --tb=short --durations=15 --junitxml=junit-full.xml` |
| Финальная фаза | `.\.venv\Scripts\python.exe scripts/run_last_admin_tests.py` |

Для полного локального прогона выполните обе фазы по порядку. Без `JWT_SECRET` локально пропускается [сценарий истечения JWT](../tests/auth/test_token_expiration.py#L26).

### Последний активный администратор

[Скрипт финальной фазы](../scripts/run_last_admin_tests.py) поднимает временный стенд, поскольку подготовка меняет роли администраторов. Для запуска нужен образ API `hotel-booking-api`, который Compose собирает с настройками по умолчанию. Результат сохраняется в `junit-last-admin-isolated.xml`. Флаг `--reuse-ci-stand` используется только в CI.

### PostgreSQL в тестах

Для тестов с меткой `db`, в том числе части тестов в `tests/bookings/`, нужен `TEST_DATABASE_URL`. Тесты через SQL меняют даты тестовых броней и читают сохранённые данные. Статусы брони и платежа меняет само приложение. [Код работы с БД](../db.py).

## Allure и результаты CI

Для локального HTML-отчёта используйте Node.js с npm и Java. В CI используются Node.js 24 и Java 17. Из корня автотестов:

```powershell
.\.venv\Scripts\python.exe -m pytest -m smoke -q --alluredir=artifacts/allure-results --clean-alluredir
npm.cmd exec --yes --package=allure-commandline@2.46.1 -- allure generate artifacts/allure-results --output artifacts/allure-report --single-file --clean
```

Откройте `artifacts/allure-report/index.html`.

В [GitHub Actions → API tests](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml) через **Run workflow** можно запустить `smoke` или `full` на временном стенде. В **Summary** видны результаты фаз и версии API и тестов.

В **Artifacts** скачайте `api-tests-smoke` или `api-tests-full`. В архиве находятся Allure HTML, JUnit и журналы контейнеров `compose.log`. В `full` отчёт Allure объединяет обе фазы. Если прогон оборвался до тестов, отчётов может не быть. Архив хранится 14 дней.

## Диагностика

Если API не готов, в каталоге приложения выполните:

```powershell
docker compose ps -a
docker compose logs --tail 100 init api worker db
```

Локальные интерфейсы: [Swagger](http://localhost:8000/docs), [OpenAPI](http://localhost:8000/openapi.json). При падении сопоставьте HTTP-ответ, request ID, Allure/JUnit и логи с версией API.

