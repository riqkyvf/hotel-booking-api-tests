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

[Документы о контракте API и БД](#контракт)

## Карта покрытия API

Карта сопоставляет [29 операций спецификации](api-specification.md) с проверками в `tests/`. Общий префикс путей — `/api/v1`.

Набор проверяет пользовательские и административные сценарии, включая изоляцию данных, повторы с `Idempotency-Key`, конкурентные запросы и историю переходов в PostgreSQL.

### Пользователи и авторизация

| Операция | Что проверяется и где |
|---|---|
| POST `/auth/register` | Нормализация, валидация, дубликаты и создание профиля. [Тесты](testing-auth.md#registration-checklist) |
| POST `/auth/login` | Вход, валидация, неверные данные и отключённый пользователь. [Тесты](testing-auth.md#login-checklist) |
| GET `/users/me` | Данные владельца, доступ с JWT и деактивация. [Тесты](testing-auth.md#authorization) |
| PATCH `/users/me` | Частичное изменение, очистка телефона, конфликт email и отказ без изменений. [Тесты](testing-auth.md#profile-checklist) |

### Отели

| Операция | Что проверяется и где |
|---|---|
| GET `/hotels` | Фильтры, цены, сортировка, две страницы и пустая выдача, архивность. [Тесты](testing-hotels.md#hotels-checklist) |
| GET `/hotels/{hotel_id}` | Схема ответа, ошибки ID и доступ к архивным отелям по ролям. [Тесты](testing-hotels.md#hotels-checklist) |
| POST `/hotels` | Создание, валидация, сохранение и права. [Тесты](testing-hotels.md#hotel-management) |
| PUT `/hotels/{hotel_id}` | Полное обновление, валидация, запрет обновлять архивный отель и сохранность данных при отказе. [Тесты](testing-hotels.md#hotel-management) |
| DELETE `/hotels/{hotel_id}` | Архив с номером, повтор и запрет при действующей брони. [Тесты](testing-hotels.md#hotel-management) |

### Номера и доступность

| Операция | Что проверяется и где |
|---|---|
| GET `/hotels/{hotel_id}/rooms` | Фильтры, сортировка, страницы, роли и архивность. [Тесты](testing-hotels.md#room-creation-reading) |
| GET `/rooms/{room_id}` | Схема, UUID и чтение отключённого или архивного номера. [Тесты](testing-hotels.md#room-creation-reading) |
| POST `/hotels/{hotel_id}/rooms` | Валидация, уникальность номера в отеле, запрет создания в архивном отеле и права доступа. [Тесты](testing-hotels.md#room-creation-reading) |
| PUT `/rooms/{room_id}` | Обновление, дубликат, ограничения вместимости и архивность. [Тесты](testing-hotels.md#room-management) |
| PATCH `/rooms/{room_id}/availability` | Отключение, включение, валидация и оплата прежней брони. [Тесты](testing-hotels.md#room-management) |
| DELETE `/rooms/{room_id}` | Архивирование, повтор и защита действующей брони. [Тесты](testing-hotels.md#room-management) |
| GET `/rooms/{room_id}/availability` | Цена, границы дат и числа гостей, причины отказа и освобождение дат. [Тесты](testing-bookings.md#room-availability) |

### Бронирования

| Операция | Что проверяется и где |
|---|---|
| POST `/bookings` | Создание, валидация, повтор ключа после оплаты, отмены, истечения или завершения. [Идемпотентность](testing-bookings.md#repeated-requests-checklist), [конкуренция](testing-bookings.md#booking-concurrency) |
| GET `/bookings` | Фильтры, в том числе `expired` и `completed`, сортировка, страницы и изоляция владельцев. [Тесты](testing-bookings.md#booking-list) |
| GET `/bookings/{booking_id}` | Схема, состояния, UUID и права владельца и admin. [Тесты](testing-bookings.md#booking-payment-reading) |
| PATCH `/bookings/{booking_id}/cancel` | Возврат, повтор, права, запреты по состояниям и гонка с оплатой. [Сценарии](testing-bookings.md#booking-cancellation-checklist), [UUID](testing-bookings.md#booking-payment-mutation-ids) |

### Платежи

| Операция | Что проверяется и где |
|---|---|
| POST `/bookings/{booking_id}/payments` | Создание, повторы, запреты по состояниям и конкурентный запрос. [Сценарии](testing-bookings.md#payment-concurrency), [UUID](testing-bookings.md#booking-payment-mutation-ids) |
| GET `/payments/{payment_id}` | Схема, UUID, состояния и доступ. [Тесты](testing-bookings.md#booking-payment-reading) |
| POST `/payments/{payment_id}/simulate-success` | Подтверждение брони, повторы, сроки, права и конкуренция. [Сценарии](testing-bookings.md#payment-success-concurrency), [UUID](testing-bookings.md#booking-payment-mutation-ids) |
| POST `/payments/{payment_id}/simulate-failure` | Отказ с причиной, повтор, валидация и запреты по состояниям. [Сценарии](testing-bookings.md#payment-failure-checklist), [UUID](testing-bookings.md#booking-payment-mutation-ids) |

### Администрирование и health

| Операция | Что проверяется и где |
|---|---|
| GET `/admin/users` | Фильтры, сортировка, пагинация, права и отсутствие секретов. [Тесты](testing-auth.md#admin-users) |
| GET `/admin/users/{user_id}` | Чтение, UUID, права и отсутствие секретов. [Тесты](testing-auth.md#admin-users) |
| PATCH `/admin/users/{user_id}` | Роль, активность, сохранность броней и защита последнего admin. [Тесты](testing-auth.md#admin-users) |
| GET `/health/live` | HTTP 200 и `status=alive` без токена. [Тесты](../tests/test_health.py) |
| GET `/health/ready` | HTTP 200 и `status=ready` без токена. [Тесты](../tests/test_health.py) |

### Вне текущего API-набора

- Полный перебор однотипных входов. Для HTTP-валидации используются показательные значения.
- Проверка алгоритма хранения паролей относится к тестам приложения с БД.
- Имитация отказов инфраструктуры относится к проверкам на отдельном стенде.

<a id="smoke-suite"></a>

## Smoke-набор

Маркер `smoke` выбирает 19 проверок основного пути и критичных отказов.

В Allure у smoke-сценариев есть читаемые заголовки, а у многошаговых проверок видны основные действия и проверка результата. [Запуск smoke](../README.md#быстрый-старт)

| Существующие тесты | Случаев | Зачем включены |
|---|---:|---|
| [test_health_returns_success](../tests/test_health.py) — live/ready | 2 | API отвечает и сообщает готовность инфраструктуры |
| [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py) | 1 | Регистрация, вход, выдача рабочего токена и чтение собственного профиля |
| [test_hotels_default_pagination](../tests/test_hotels.py) | 1 | Публичный каталог отелей возвращает корректную страницу |
| [test_get_hotel_for_each_role](../tests/test_hotels.py) — гость, пользователь, администратор | 3 | Детали отеля доступны с токенами обеих ролей и без токена |
| [test_booking_flow.py](../tests/test_booking_flow.py) — все три теста | 3 | Список/детали номеров, доступность, создание/чтение/список брони, расчёт суммы, оплата и confirmed/succeeded |
| [test_cancellation_releases_room_for_another_user](../tests/test_booking_cancellation.py) — без платежа/pending/оплачена | 3 | Отмена освобождает даты для другого пользователя; платёж отменяется или возвращается по исходному состоянию |
| [test_overlapping_booking_is_rejected](../tests/test_booking_overlap.py) — только same_dates, pending_payment/confirmed | 2 | Двойное бронирование одинаковых дат запрещено до и после оплаты |
| [test_protected_operations_reject_invalid_credentials](../tests/test_authorization.py) — только missing, три операции | 3 | Профиль, список броней и создание отеля недоступны без токена: 401 |
| [test_user_cannot_create_hotel](../tests/test_admin_operations_access.py) | 1 | Обычный пользователь получает 403 на admin-операцию, отель не создаётся |

## Запуск отдельного приложения

Запустите Docker. Для первого запуска откройте PowerShell в папке, где храните проекты, и клонируйте репозиторий приложения. Если он уже клонирован, перейдите в его каталог и выполните две последние команды.

```powershell
git clone https://github.com/riqkyvf/hotel-booking-api.git
Set-Location hotel-booking-api
docker compose up --build --wait
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

Когда проверка вернёт `status: ready`, вернитесь в каталог автотестов и выполните [быстрый старт](../README.md#быстрый-старт). Команда из README создаст локальный `.env` из шаблона этого репозитория.

Для отладки доступны [Swagger](http://localhost:8000/docs) и [OpenAPI](http://localhost:8000/openapi.json). Если API не готов, выполните в каталоге приложения `docker compose ps -a` и `docker compose logs --tail 100 init api worker db`.

Учётные записи, DBeaver, миграции и сброс данных описаны в [README приложения](https://github.com/riqkyvf/hotel-booking-api#readme).

## Контракт

- [Требования](requirements.md)
- [Спецификация REST API](api-specification.md)
- [Расчёт стоимости и переходы состояний](business-rules.md)
- [Ограничения PostgreSQL](database-schema.md)
