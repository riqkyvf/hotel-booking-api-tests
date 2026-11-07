# Документация и эксплуатация

Команды для запуска автотестов находятся в [главном README](../README.md#быстрый-старт).

## Навигация

[Карта покрытия 29 операций API](#карта-покрытия-api) — проверяемые сценарии и ссылки на тесты. [Smoke-набор](#smoke-suite) — быстрые проверки основных функций.

| Документ | Назначение |
|---|---|
| [Пользователи и авторизация](testing-auth.md) | Регистрация, вход, профиль и административные права |
| [Каталог отелей и номеров](testing-hotels.md) | Создание номеров, чтение, фильтры, сортировка, цены и архивность |
| [Бронирование и платежи](testing-bookings.md) | Основной путь, ограничения, отмена, истечение, доступ и повторы |
| [GitHub Actions](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml) | Результаты CI, коммиты и артефакты Allure |

[Локальный отчёт Allure](#локальный-отчёт-allure) · [Документы о контракте API и работе с БД](#контракт)

## Карта покрытия API

Карта сопоставляет [29 операций спецификации](https://github.com/riqkyvf/hotel-booking-api/blob/main/docs/api-specification.md) с проверками в `tests/`. Общий префикс путей — `/api/v1`.

### Пользователи и авторизация

| Операция | Что проверяется и где |
|---|---|
| POST `/auth/register` | Создание пользователя и валидация. [Сценарии](testing-auth.md#registration-checklist) |
| POST `/auth/login` | Выдача токена и отказы во входе. [Сценарии](testing-auth.md#login-checklist) |
| GET `/users/me` | Профиль и доступ с JWT. [Сценарии](testing-auth.md#authorization) |
| PATCH `/users/me` | Частичное обновление и сохранность профиля при отказе. [Сценарии](testing-auth.md#profile-checklist) |

### Отели

| Операция | Что проверяется и где |
|---|---|
| GET `/hotels` | Каталог, фильтры и порядок выдачи. [Сценарии](testing-hotels.md#hotels-checklist) |
| GET `/hotels/{hotel_id}` | Детали и доступ к архиву. [Сценарии](testing-hotels.md#hotels-checklist) |
| POST `/hotels` | Создание и валидация. [Сценарии](testing-hotels.md#hotel-management) |
| PUT `/hotels/{hotel_id}` | Полное обновление и отказы без изменения данных. [Сценарии](testing-hotels.md#hotel-management) |
| DELETE `/hotels/{hotel_id}` | Архивирование и защита действующих броней. [Сценарии](testing-hotels.md#hotel-management) |

### Номера и доступность

| Операция | Что проверяется и где |
|---|---|
| GET `/hotels/{hotel_id}/rooms` | Каталог номеров и порядок выдачи. [Сценарии](testing-hotels.md#room-creation-reading) |
| GET `/rooms/{room_id}` | Детали и видимость номера. [Сценарии](testing-hotels.md#room-creation-reading) |
| POST `/hotels/{hotel_id}/rooms` | Создание, валидация и уникальность. [Сценарии](testing-hotels.md#room-creation-reading) |
| PUT `/rooms/{room_id}` | Обновление и ограничения при действующей брони. [Сценарии](testing-hotels.md#room-management) |
| PATCH `/rooms/{room_id}/availability` | Управление доступностью и сохранность прежней брони. [Сценарии](testing-hotels.md#room-management) |
| DELETE `/rooms/{room_id}` | Архивирование и защита действующих броней. [Сценарии](testing-hotels.md#room-management) |
| GET `/rooms/{room_id}/availability` | Доступность и стоимость проживания. [Сценарии](testing-bookings.md#room-availability) |

### Бронирования

| Операция | Что проверяется и где |
|---|---|
| POST `/bookings` | [Создание](testing-bookings.md#booking-payment-checklist), [валидация](testing-bookings.md#booking-restrictions-checklist), [идемпотентность](testing-bookings.md#repeated-requests-checklist) и [конкуренция](testing-bookings.md#booking-concurrency) |
| GET `/bookings` | Выборка броней и изоляция владельцев. [Сценарии](testing-bookings.md#booking-list) |
| GET `/bookings/{booking_id}` | Детали в разных состояниях и права доступа. [Сценарии](testing-bookings.md#booking-payment-reading) |
| PATCH `/bookings/{booking_id}/cancel` | Отмена, возврат и повтор операции. [Сценарии](testing-bookings.md#booking-cancellation-checklist), [гонка с оплатой](testing-bookings.md#payment-cancellation-concurrency) |

### Платежи

| Операция | Что проверяется и где |
|---|---|
| POST `/bookings/{booking_id}/payments` | [Создание](testing-bookings.md#booking-payment-checklist), [повторы](testing-bookings.md#repeated-requests-checklist) и [конкуренция](testing-bookings.md#payment-concurrency) |
| GET `/payments/{payment_id}` | Детали и права доступа. [Сценарии](testing-bookings.md#booking-payment-reading) |
| POST `/payments/{payment_id}/simulate-success` | Подтверждение брони и защита от повторной оплаты. [Основной путь](testing-bookings.md#booking-payment-checklist), [конкуренция](testing-bookings.md#payment-success-concurrency) |
| POST `/payments/{payment_id}/simulate-failure` | Отказ оплаты и новая попытка. [Сценарии](testing-bookings.md#payment-failure-checklist) |

### Администрирование и health

| Операция | Что проверяется и где |
|---|---|
| GET `/admin/users` | Выборка пользователей и права доступа. [Сценарии](testing-auth.md#admin-users) |
| GET `/admin/users/{user_id}` | Чтение пользователя без секретов. [Сценарии](testing-auth.md#admin-users) |
| PATCH `/admin/users/{user_id}` | Изменение прав и защита последнего администратора. [Сценарии](testing-auth.md#admin-users) |
| GET `/health/live` | HTTP 200 и `status=alive` без токена. [Тесты](../tests/test_health.py) |
| GET `/health/ready` | HTTP 200 и `status=ready` без токена. [Тесты](../tests/test_health.py) |

### Вне текущего API-набора

- Полный перебор однотипных входов. Для HTTP-валидации используются показательные значения.
- Проверка алгоритма хранения паролей относится к тестам приложения с БД.
- Имитация отказов инфраструктуры относится к проверкам на отдельном стенде.

<a id="smoke-suite"></a>

## Smoke-набор

Маркер `smoke` выбирает 14 проверок основного пути бронирования. Ключевые отказы — доступ к списку броней без токена и попытка забронировать занятые даты.

В Allure у smoke-сценариев есть читаемые заголовки, а у многошаговых проверок видны основные действия и проверка результата. [Запуск smoke](../README.md#быстрый-старт)

| Существующие тесты | Случаев | Зачем включены |
|---|---:|---|
| [test_health_returns_success](../tests/test_health.py) — live/ready | 2 | API отвечает и сообщает готовность инфраструктуры |
| [test_registered_user_can_login_and_get_profile](../tests/auth/test_auth_flow.py) | 1 | Регистрация, вход, выдача рабочего токена и чтение собственного профиля |
| [test_hotels_default_pagination](../tests/hotels/test_hotels.py) | 1 | Публичный каталог отелей возвращает корректную страницу |
| [test_get_hotel_for_each_role](../tests/hotels/test_hotels.py) — гость | 1 | Детали отеля доступны без токена |
| [test_booking_flow.py](../tests/bookings/test_booking_flow.py) — все три теста | 3 | Список/детали номеров, доступность, создание/чтение/список брони, расчёт суммы, оплата и confirmed/succeeded |
| [test_cancellation_releases_room_for_another_user](../tests/bookings/test_booking_cancellation.py) — без платежа/pending/оплачена | 3 | Отмена освобождает даты для другого пользователя; платёж отменяется или возвращается по исходному состоянию |
| [test_overlapping_booking_is_rejected](../tests/bookings/test_booking_overlap.py) — только same_dates, pending_payment/confirmed | 2 | Двойное бронирование одинаковых дат запрещено до и после оплаты |
| [test_protected_operations_reject_invalid_credentials](../tests/auth/test_authorization.py) — bookings-missing | 1 | Список броней недоступен без токена — HTTP 401 |

## Запуск отдельного приложения

Запустите Docker. Для первого запуска откройте PowerShell в папке, где храните проекты, и клонируйте репозиторий приложения. Если он уже клонирован, перейдите в его каталог и выполните две последние команды.

```powershell
git clone https://github.com/riqkyvf/hotel-booking-api.git
Set-Location hotel-booking-api
docker compose up --build --wait
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

Когда проверка вернёт `status: ready`, переходите к клонированию и запуску автотестов в [быстром старте](../README.md#быстрый-старт). Команда из README создаст локальный `.env` из шаблона репозитория автотестов.

Для отладки доступны [Swagger](http://localhost:8000/docs) и [OpenAPI](http://localhost:8000/openapi.json). Если API не готов, выполните в каталоге приложения `docker compose ps -a` и `docker compose logs --tail 100 init api worker db`.

Учётные записи, DBeaver, миграции и сброс данных описаны в [README приложения](https://github.com/riqkyvf/hotel-booking-api#readme).

## Локальный отчёт Allure

Нужны Node.js 24 и Java 17 или 21. Проверьте, что в PowerShell работают `npm.cmd --version` и `java -version`. В каталоге автотестов выполните smoke и сгенерируйте HTML:

```powershell
.\.venv\Scripts\python.exe -m pytest -m smoke -q --alluredir=artifacts/allure-results --clean-alluredir
npm.cmd exec --yes --package=allure-commandline@2.46.1 -- allure generate artifacts/allure-results --output artifacts/allure-report --single-file --clean
```

Откройте `artifacts/allure-report/index.html` в браузере. Папка `artifacts/` исключена из Git.

## Контракт

Полные требования и спецификация хранятся в ветке `main` репозитория API и описывают актуальный контракт. Для воспроизводимости версия приложения в [CI](../.github/workflows/api-tests.yml) закреплена отдельным коммитом и может отставать от документации.

- [Требования](https://github.com/riqkyvf/hotel-booking-api/blob/main/docs/requirements.md)
- [Спецификация REST API](https://github.com/riqkyvf/hotel-booking-api/blob/main/docs/api-specification.md)
- [Расчёт стоимости и переходы состояний](business-rules.md)
- [Работа тестов с PostgreSQL](database-schema.md)
