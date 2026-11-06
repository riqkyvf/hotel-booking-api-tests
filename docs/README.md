# Документация и эксплуатация

Основная инструкция запуска тестов: [README проекта](../README.md).

## Навигация

[Карта покрытия 29 операций API](#карта-покрытия-api) — сценарии и пробелы. [Smoke-набор](#smoke-suite) — быстрые проверки основных функций.

| Документ | Назначение |
|---|---|
| [Пользователи и авторизация](testing-auth.md) | Регистрация, вход, профиль, открытые вопросы |
| [Каталог отелей и номеров](testing-hotels.md) | Создание номеров, чтение, фильтры, сортировка, цены и архивность |
| [Бронирование и платежи](testing-bookings.md) | Основной путь, ограничения, отмена, истечение, доступ и повторы |
| [GitHub Actions](https://github.com/riqkyvf/hotel-booking-api-tests/actions/workflows/api-tests.yml) | Результаты CI, коммиты и артефакты Allure |

Контракт продукта описан в нормативных документах ниже. Тестовые документы связывают сценарии с автотестами.

## Карта покрытия API

Карта сопоставляет [29 операций спецификации](api-specification.md) с проверками в `tests/`. Общий префикс путей — `/api/v1`.

**Сценарии** — есть проверки основного поведения и отказов. **Частично** — проверены отдельные стороны контракта. В колонке пробелов `—` означает, что приоритетных задач по операции не выделено.

### Пользователи и авторизация

| Операция | Уровень | Что проверяется и где | Основные пробелы |
|---|---|---|---|
| POST `/auth/register` | Сценарии | Нормализация, валидация, дубликаты и создание профиля. [Тесты](testing-auth.md#registration-checklist) | Одновременная регистрация одного email |
| POST `/auth/login` | Сценарии | Вход, валидация, неверные данные и отключённый пользователь. [Тесты](testing-auth.md#login-checklist) | — |
| GET `/users/me` | Частично | Данные владельца, доступ с JWT и деактивация. [Тесты](testing-auth.md#authorization) | — |
| PATCH `/users/me` | Сценарии | Частичное изменение, очистка телефона, конфликт email и отказ без изменений. [Тесты](testing-auth.md#profile-checklist) | — |

### Отели

| Операция | Уровень | Что проверяется и где | Основные пробелы |
|---|---|---|---|
| GET `/hotels` | Сценарии | Фильтры, цены, сортировка, страницы и архивность. [Тесты](testing-hotels.md#hotels-checklist) | — |
| GET `/hotels/{hotel_id}` | Сценарии | Схема, UUID, роли и архивность. [Тесты](testing-hotels.md#hotels-checklist) | — |
| POST `/hotels` | Сценарии | Создание, валидация, сохранение и права. [Тесты](testing-hotels.md#hotel-management) | — |
| PUT `/hotels/{hotel_id}` | Сценарии | Полное обновление, валидация, архив и сохранность при отказе. [Тесты](testing-hotels.md#hotel-management) | — |
| DELETE `/hotels/{hotel_id}` | Сценарии | Архив с номером, повтор и запрет при действующей брони. [Тесты](testing-hotels.md#hotel-management) | Архивирование отеля с несколькими номерами |

### Номера и доступность

| Операция | Уровень | Что проверяется и где | Основные пробелы |
|---|---|---|---|
| GET `/hotels/{hotel_id}/rooms` | Сценарии | Фильтры, сортировка, страницы, роли и архивность. [Тесты](testing-hotels.md#room-creation-reading) | Сквозное чтение страниц без повторов |
| GET `/rooms/{room_id}` | Сценарии | Схема, UUID и чтение отключённого или архивного номера. [Тесты](testing-hotels.md#room-creation-reading) | Неверный необязательный JWT |
| POST `/hotels/{hotel_id}/rooms` | Сценарии | Валидация, уникальность номера, родитель и права. [Тесты](testing-hotels.md#room-creation-reading) | Сломанный JSON и лишние поля |
| PUT `/rooms/{room_id}` | Сценарии | Обновление, дубликат, ограничения вместимости и архивность. [Тесты](testing-hotels.md#room-management) | Обновление отключённого номера |
| PATCH `/rooms/{room_id}/availability` | Сценарии | Отключение, включение, валидация и оплата прежней брони. [Тесты](testing-hotels.md#room-management) | — |
| DELETE `/rooms/{room_id}` | Сценарии | Архивирование, повтор и защита действующей брони. [Тесты](testing-hotels.md#room-management) | Архивирование после завершения действующей брони |
| GET `/rooms/{room_id}/availability` | Сценарии | Цена, параметры, причины отказа и освобождение дат. [Тесты](testing-bookings.md#room-availability) | Доступность на точной границе истечения удержания |

### Бронирования

| Операция | Уровень | Что проверяется и где | Основные пробелы |
|---|---|---|---|
| POST `/bookings` | Сценарии | Создание, валидация, повтор ключа после оплаты, отмены, истечения или завершения. [Идемпотентность](testing-bookings.md#repeated-requests-checklist), [конкуренция](testing-bookings.md#booking-concurrency) | — |
| GET `/bookings` | Сценарии | Фильтры, в том числе `expired` и `completed`, сортировка, страницы и доступ. [Тесты](testing-bookings.md#booking-list) | — |
| GET `/bookings/{booking_id}` | Сценарии | Схема, состояния, UUID и права владельца и admin. [Тесты](testing-bookings.md#booking-payment-reading) | — |
| PATCH `/bookings/{booking_id}/cancel` | Сценарии | Возврат, повтор, права, запреты по состояниям и гонка с оплатой. [Сценарии](testing-bookings.md#booking-cancellation-checklist), [UUID](testing-bookings.md#booking-payment-mutation-ids) | Повтор после заезда и гонка двух отмен |

### Платежи

| Операция | Уровень | Что проверяется и где | Основные пробелы |
|---|---|---|---|
| POST `/bookings/{booking_id}/payments` | Сценарии | Создание, повторы, запреты по состояниям и конкурентный запрос. [Сценарии](testing-bookings.md#payment-concurrency), [UUID](testing-bookings.md#booking-payment-mutation-ids) | — |
| GET `/payments/{payment_id}` | Сценарии | Схема, UUID, состояния и доступ. [Тесты](testing-bookings.md#booking-payment-reading) | — |
| POST `/payments/{payment_id}/simulate-success` | Сценарии | Подтверждение брони, повторы, сроки, права и конкуренция. [Сценарии](testing-bookings.md#payment-success-concurrency), [UUID](testing-bookings.md#booking-payment-mutation-ids) | Гонка оплаты с истечением |
| POST `/payments/{payment_id}/simulate-failure` | Сценарии | Отказ с причиной, повтор, валидация и запреты по состояниям. [Сценарии](testing-bookings.md#payment-failure-checklist), [UUID](testing-bookings.md#booking-payment-mutation-ids) | Одновременные симуляции успеха и отказа |

### Администрирование и health

| Операция | Уровень | Что проверяется и где | Основные пробелы |
|---|---|---|---|
| GET `/admin/users` | Сценарии | Фильтры, сортировка, пагинация, права и отсутствие секретов. [Тесты](testing-auth.md#admin-users) | — |
| GET `/admin/users/{user_id}` | Сценарии | Чтение, UUID, права и отсутствие секретов. [Тесты](testing-auth.md#admin-users) | — |
| PATCH `/admin/users/{user_id}` | Сценарии | Роль, активность, сохранность броней и защита последнего admin. [Тесты](testing-auth.md#admin-users) | Одновременные изменения роли или активности последних двух администраторов |
| GET `/health/live` | Частично | HTTP 200 и `status=alive` без токена. [Тесты](../tests/test_health.py) | — |
| GET `/health/ready` | Частично | HTTP 200 и `status=ready` без токена. [Тесты](../tests/test_health.py) | HTTP 503 при неготовности БД |

**Итого: 26 операций со сценариями, 3 покрыты частично.**

Общие задачи: дополнить схемы успешных ответов профиля и списков броней и пользователей в существующих тестах. Проверки `exp`, `iss` и `aud` остаются задачей [общей авторизации](testing-auth.md#authorization).

<a id="smoke-suite"></a>

## Smoke-набор

Маркер `smoke` выбирает 19 проверок основного пути и критичных отказов.

```powershell
.\.venv\Scripts\python.exe -m pytest -m smoke -q
```

| Существующие тесты | Случаев | Зачем включены |
|---|---:|---|
| [test_health_returns_success](../tests/test_health.py) — live/ready | 2 | API отвечает и сообщает готовность инфраструктуры |
| [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py) | 1 | Регистрация, вход, выдача рабочего токена и чтение собственного профиля |
| [test_hotels_default_pagination](../tests/test_hotels.py) | 1 | Публичный каталог отелей возвращает корректную страницу |
| [test_get_hotel_for_each_role](../tests/test_hotels.py) — guest/user/admin | 3 | Данные собственного отеля читаются всеми предусмотренными ролями |
| [test_booking_flow.py](../tests/test_booking_flow.py) — все три теста | 3 | Список/детали номеров, доступность, создание/чтение/список брони, расчёт суммы, оплата и confirmed/succeeded |
| [test_cancellation_releases_room_for_another_user](../tests/test_booking_cancellation.py) — без платежа/pending/оплачена | 3 | Отмена освобождает даты для другого пользователя; платёж отменяется или возвращается по исходному состоянию |
| [test_overlapping_booking_is_rejected](../tests/test_booking_overlap.py) — только same_dates, pending_payment/confirmed | 2 | Двойное бронирование одинаковых дат запрещено до и после оплаты |
| [test_protected_operations_reject_invalid_credentials](../tests/test_authorization.py) — только missing, три операции | 3 | Профиль, список броней и создание отеля недоступны без токена: 401 |
| [test_user_cannot_create_hotel](../tests/test_admin_operations_access.py) | 1 | Обычный пользователь получает 403 на admin-операцию, отель не создаётся |

Для smoke нужны работающий API и учётные данные администратора из `.env`. [Команды запуска](../README.md#быстрый-старт)

## Запуск отдельного приложения

Запустите Docker и выполните команды в PowerShell. Если API уже клонирован, перейдите в его каталог и начните с Compose.

```powershell
git clone https://github.com/riqkyvf/hotel-booking-api.git
Set-Location hotel-booking-api
docker compose up --build --wait
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

После HTTP 200 вернитесь в каталог автотестов и настройте `.env` по [примеру](../.env.example). Для отладки доступны [Swagger](http://localhost:8000/docs) и [OpenAPI](http://localhost:8000/openapi.json). При сбое стенда проверьте `docker compose ps -a` и `docker compose logs --tail 100 init api worker db`.

Учётные записи, DBeaver, миграции и сброс данных описаны в [README приложения](https://github.com/riqkyvf/hotel-booking-api#readme).

## Контракт

- [Требования](requirements.md)
- [Спецификация REST API](api-specification.md)
- [Расчёт стоимости и переходы состояний](business-rules.md)
- [Ограничения PostgreSQL](database-schema.md)
