# Бронирования: создание и работа с ресурсами

Контракт API: [REST-спецификация](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/api-specification.md#бронирования) и [требования](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md) версии из [CI](../.github/workflows/api-tests.yml). Локальные пояснения: [модель бизнес-правил](business-rules.md).

Сценарии с меткой `db` используют PostgreSQL для подготовки дат и проверки сохранённых состояний. Статусы меняет приложение. [Настройки подключения](../README.md#быстрый-старт) · [Как читать каталог](README.md#check-catalog).

**Разделы:** [создание](#booking-payment-checklist) · [доступность и пересечения](#booking-restrictions-checklist) · [права](#booking-access-checklist) · [списки и детали](#список-и-детали) · [изменения номера](#room-booking-integrity) · [идемпотентность](#repeated-requests-checklist) · [конкуренция](#конкурентные-запросы).

Оплата, отмена, истечение и завершение — в [матрице жизненного цикла](testing-booking-lifecycle.md).

<a id="booking-payment-checklist"></a>

## Создание брони

Источник: FR-04 (владелец, даты, гости, цена, удержание), FR-03 (состояние номера и снимок цены), FR-06 (ключ не расходуется при ошибке) и REST-спецификация версии из начала документа. Общие условия: новый пользователь, отдельный доступный номер, валидный новый `Idempotency-Key`; кроме явно изменяемых полей запрос корректен.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| BKG-001 | <a id="bkg-001"></a>Создание → `201`, UUID, `pending_payment`, текущий пользователь — владелец; бронь сохраняется и читается | Обычный пользователь; GET и собственный список; `smoke` | Высокая | Покрыто | [test_user_can_create_and_read_booking](../tests/bookings/test_booking_flow.py) |
| BKG-002 | <a id="bkg-002"></a>Цена рассчитывается сервером: цена за ночь × число ночей, валюта RUB, денежные поля — строки | `1234.56 × 3`; 1 и 14 ночей | Высокая | Покрыто | [test_user_can_create_and_read_booking](../tests/bookings/test_booking_flow.py), [test_booking_with_valid_stay_boundaries_is_allowed](../tests/bookings/test_booking_restrictions.py) |
| BKG-003 | <a id="bkg-003"></a>Новая бронь удерживается 30 минут от `decision_time` | Обычный POST: expires_at между временем отправки/получения + 30 минут, допуск ±5 с; часы API/БД и runner синхронизированы в пределах допуска | Высокая | Частично: длительность ограничена временным окном; момент решения после ожидания блокировок не изолирован | [test_user_can_create_and_read_booking](../tests/bookings/test_booking_flow.py) |
| BKG-004 | <a id="bkg-004"></a>Заезд сегодня и длительность 1–14 ночей разрешены → `201`, сумма и сохранённые данные верны | check_in_today — 3 ночи/2 гостя; one_night — 1 ночь/1 гость; fourteen_nights — 14 ночей/10 гостей | Высокая | Покрыто | [test_booking_with_valid_stay_boundaries_is_allowed](../tests/bookings/test_booking_restrictions.py) |
| BKG-005 | <a id="bkg-005"></a>Заезд в прошлом → `422 PAST_CHECK_IN`, бронь не создаётся | Вчера по UTC, выезд завтра | Высокая | Покрыто | [test_booking_with_past_check_in_is_rejected](../tests/bookings/test_booking_restrictions.py) |
| BKG-006 | <a id="bkg-006"></a>Выезд не позже заезда или проживание больше 14 ночей → `422 VALIDATION_ERROR`, бронь не создаётся | `same_day`, `before_check_in`; 15 ночей | Высокая | Покрыто | [test_booking_with_check_out_not_after_check_in_is_rejected](../tests/bookings/test_booking_restrictions.py), [test_booking_longer_than_fourteen_nights_is_rejected](../tests/bookings/test_booking_restrictions.py) |
| BKG-007 | <a id="bkg-007"></a>Вместимость нельзя превысить → `409 CAPACITY_EXCEEDED`, бронь не создаётся | 3 гостя при вместимости 2, число гостей в допустимом диапазоне 1–10 | Высокая | Покрыто | [test_booking_exceeding_room_capacity_is_rejected](../tests/bookings/test_booking_restrictions.py) |
| BKG-008 | <a id="bkg-008"></a>Отключённый номер нельзя бронировать → `409 ROOM_DISABLED`, номер неизменен, новой брони нет | `is_available=false`, неархивный номер | Высокая | Покрыто | [test_booking_disabled_room_is_rejected](../tests/bookings/test_booking_restrictions.py) |
| BKG-009 | <a id="bkg-009"></a>Архивный номер нельзя бронировать → `404 NOT_FOUND`, новой брони нет | Номер архивирован через API | Высокая | Покрыто | [test_booking_archived_room_is_rejected](../tests/bookings/test_booking_restrictions.py) |
| BKG-010 | <a id="bkg-010"></a>Клиент не задаёт цену, владельца, статус и неизвестные поля → `422 VALIDATION_ERROR`, новой брони нет | Цена `"0.01"` в `total_price` / `price_per_night`; `user_id="someone_else"`, `status="confirmed"`, `unexpected="value"`, по одному полю | Высокая | Частично: `user_id` с корректным UUID другого пользователя не проверен | [test_booking_rejects_invalid_body_fields](../tests/bookings/test_booking_validation.py) |
| BKG-011 | <a id="bkg-011"></a>Изменение цены номера влияет на новую бронь; прежние бронь и платёж сохраняют сумму | `1234.56 → 2345.67`; новая бронь другого пользователя на непересекающиеся даты | Высокая | Покрыто | [test_room_price_change_affects_only_new_bookings](../tests/rooms/test_room_booking_integrity.py) |
| BKG-012 | <a id="bkg-012"></a>Обязательное поле отсутствует → `422 VALIDATION_ERROR`; исправление с тем же ключом создаёт бронь | По одному: `room_id`, `check_in`, `check_out`, `guests` | Средняя | Покрыто | [test_booking_requires_fields_and_does_not_consume_key](../tests/bookings/test_booking_validation.py) |
| BKG-013 | <a id="bkg-013"></a>Гости — целое JSON-число 1–10 → иначе `422 VALIDATION_ERROR`, новой брони нет | `0`, `11`, `true`, `1.5`, строка `"2"`, `null` | Средняя | Покрыто | [test_booking_rejects_invalid_body_fields](../tests/bookings/test_booking_validation.py) |
| BKG-014 | <a id="bkg-014"></a>Неверные UUID, даты и типы → `422 VALIDATION_ERROR` нужного поля, новой брони нет | `room_id`: `not-a-uuid`, `null`; даты: месяц 13, 30 февраля, timestamp вместо даты, число для выезда, `null` обоих полей | Средняя | Покрыто | [test_booking_rejects_invalid_body_fields](../tests/bookings/test_booking_validation.py) |
| BKG-015 | <a id="bkg-015"></a>Некорректное JSON-тело → `422 VALIDATION_ERROR`; ключ доступен для исправленного запроса | `malformed_json`, `array` | Средняя | Покрыто | [test_booking_rejects_invalid_json_body](../tests/bookings/test_booking_validation.py) |
| BKG-016 | <a id="bkg-016"></a>Границы числа гостей 1 и 10 разрешены → `201`, число гостей сохранено | 1 гость при вместимости 2; 10 гостей при вместимости 10; GET и список подтверждают бронь | Высокая | Покрыто | [test_booking_with_valid_stay_boundaries_is_allowed](../tests/bookings/test_booking_restrictions.py) |
| BKG-017 | <a id="bkg-017"></a>Номер архивного отеля нельзя бронировать → `404 NOT_FOUND` | Архивирование отеля, затем POST брони его номера | Высокая | Не покрыто | — |
| BKG-018 | <a id="bkg-018"></a>Корректный UUID отсутствующего номера → `404 NOT_FOUND`, новой брони нет | `room_id` несуществующего номера в теле POST | Средняя | Не покрыто | — |

Варианты границ дат заданы в [data/booking.py](../data/booking.py). BKG-017–018 не найдены в просмотренном наборе; проверки GET доступности не заменяют POST брони. Правила авторизации, ключа идемпотентности и повторов рассматриваются в соответствующих разделах.

Создание и успешная оплата платежа описаны в [PAY-001–002](testing-booking-lifecycle.md#pay-001).

<a id="booking-restrictions-checklist"></a>

## Ограничения и доступность

Ограничения POST брони приведены в BKG-004–018. Ниже — публичная проверка доступности и пересечения интервалов.

<a id="room-availability"></a>

### Доступность номера

Источник: FR-04 и раздел «Номера» REST-спецификации; порядок причин отказа дополнительно описан в локальной [модели бизнес-правил](business-rules.md#доступность). Запросы выполняются без токена; валидные даты — по UTC. Это покрытие GET `/rooms/{room_id}/availability`, а не POST брони.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| AVL-001 | <a id="avl-001"></a>Свободный номер → `200`, `available=true`, `reason=null`, правильные ночи, сумма и RUB | `today-one-night-one-guest`, `future-one-night-two-guests`, `fourteen-nights-max-guests` (14 ночей, 10 гостей); вместимость 10 | Высокая | Покрыто | [test_availability_accepts_stay_boundaries](../tests/rooms/test_room_availability.py) |
| AVL-002 | <a id="avl-002"></a>Недоступность → `200`, `available=false`; причина по порядку disabled → capacity → overlap, исходная бронь неизменна | `disabled`, `capacity`, `overlap`, `disabled_capacity`, `disabled_overlap`, `capacity_overlap`, `disabled_capacity_overlap` | Высокая | Покрыто | [test_availability_reason_priority](../tests/rooms/test_room_availability.py) |
| AVL-003 | <a id="avl-003"></a>GET не резервирует даты; только POST создаёт бронь и занимает интервал | Два GET → доступно, список пуст; POST → `201`, одна бронь; GET → `ROOM_NOT_AVAILABLE` | Высокая | Покрыто | [test_availability_get_does_not_reserve_room](../tests/rooms/test_room_availability.py) |
| AVL-004 | <a id="avl-004"></a>Отсутствуют обязательные query-параметры → `422 VALIDATION_ERROR` нужных полей | По одному `check_in`, `check_out`, `guests`; все сразу (`all`) | Средняя | Покрыто | [test_availability_requires_query_fields](../tests/rooms/test_room_availability.py) |
| AVL-005 | <a id="avl-005"></a>Неверное число гостей → `422 VALIDATION_ERROR` поля `query.guests` | Строки query: `0`, `11`, `-1`, `1.5`, `true`, `false`, `text`, пустая, `null` | Средняя | Покрыто | [test_availability_rejects_invalid_guests](../tests/rooms/test_room_availability.py) |
| AVL-006 | <a id="avl-006"></a>Неверный формат даты → `422 VALIDATION_ERROR` соответствующего query-поля | Оба поля × `2030-02-30`, пустая строка, `text`, timestamp, `2030-1-1`, `1234567890`, `null` | Средняя | Покрыто | [test_availability_rejects_invalid_date_format](../tests/rooms/test_room_availability.py) |
| AVL-007 | <a id="avl-007"></a>Неверная длительность → `422 VALIDATION_ERROR`; заезд в прошлом → `422 PAST_CHECK_IN` | 0, −1, 15 ночей; заезд вчера, выезд завтра | Средняя | Покрыто | [test_availability_rejects_invalid_duration](../tests/rooms/test_room_availability.py), [test_availability_rejects_past_check_in](../tests/rooms/test_room_availability.py) |
| AVL-008 | <a id="avl-008"></a>Отсутствующие и архивные ресурсы скрыты → `404 NOT_FOUND`; неверный UUID → `422 VALIDATION_ERROR` | `unknown`, `archived_room`, `archived_hotel`, `invalid_uuid` | Средняя | Покрыто | [test_availability_hides_missing_or_archived_resources](../tests/rooms/test_room_availability.py) |

[test_user_can_select_available_room](../tests/bookings/test_booking_flow.py) связывает поиск и чтение номера с расчётом доступности в `smoke`. Освобождение после истечения — [EXP-003](testing-booking-lifecycle.md#exp-003).

<a id="booking-overlap-checklist"></a>

### Пересечения интервалов

Источник: FR-04, интервал `[check_in, check_out)`. Существующая бронь: `blocking_booking=pending_payment` / `confirmed`; новую создаёт другой пользователь. Каждый вариант интервала проверяется в обоих состояниях, через доступность и POST брони.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| OVL-001 | <a id="ovl-001"></a>Пересечение запрещено → `409 ROOM_NOT_AVAILABLE`, новой брони нет, исходная неизменна | `same_dates`, `overlap_left`, `overlap_right`, `inside_existing`, `contains_existing` × два состояния | Высокая | Покрыто | [test_overlapping_booking_is_rejected](../tests/bookings/test_booking_overlap.py) |
| OVL-002 | <a id="ovl-002"></a>Смежные интервалы разрешены → `201`, обе брони сохранены | `ends_at_existing_check_in`, `starts_at_existing_check_out` × два состояния | Высокая | Покрыто | [test_adjacent_booking_is_allowed](../tests/bookings/test_booking_overlap.py) |
| OVL-003 | <a id="ovl-003"></a>Занятость одного номера не блокирует другой → `201`, исходная бронь неизменна | Другой номер того же отеля, совпадающие даты × два состояния | Высокая | Покрыто | [test_booking_another_room_on_same_dates_is_allowed](../tests/bookings/test_booking_overlap.py) |

Данные интервалов: [OVERLAPPING_STAYS и ADJACENT_STAYS](../data/booking.py). Одновременное создание рассматривается отдельно в [конкурентных запросах](#конкурентные-запросы).

<a id="booking-access-checklist"></a>

## Доступ к броням и платежам

Источники: FR-01 (авторизация), FR-02 (деактивация), FR-04 (изоляция броней), FR-07 (платит только владелец) и общий контракт REST-спецификации. `booking_with_payment` в [conftest.py](../tests/conftest.py) проверяет пары «бронь / платёж»: `pending_payment` / `pending` и `confirmed` / `succeeded`. Заезд в будущем, удержание не истекло.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| ACC-001 | <a id="acc-001"></a>Чужие приватные ресурсы скрыты независимо от состояния → `404 NOT_FOUND`, данные владельца неизменны | Другой обычный пользователь; бронь и платёж; оба варианта `booking_with_payment` | Высокая | Частично: терминальные состояния брони и платежа не проверены | [test_user_cannot_read_another_users_booking](../tests/bookings/test_booking_access.py), [test_user_cannot_read_another_users_payment](../tests/bookings/test_booking_access.py) |
| ACC-002 | <a id="acc-002"></a>Другой пользователь не создаёт платёж чужой брони → `404 NOT_FOUND`; владелец после отказа создаёт свой платёж | `pending_payment`, до первого платежа | Высокая | Покрыто | [test_user_cannot_create_payment_for_another_users_booking](../tests/bookings/test_booking_access.py) |
| ACC-003 | <a id="acc-003"></a>Другой пользователь не симулирует чужую оплату → `404 NOT_FOUND`, бронь и платёж неизменны | Успех и отказ × оба варианта `booking_with_payment` | Высокая | Покрыто | [test_user_cannot_simulate_success_of_another_users_payment](../tests/bookings/test_booking_access.py), [test_user_cannot_simulate_failure_of_another_users_payment](../tests/bookings/test_booking_access.py) |
| ACC-004 | <a id="acc-004"></a>Admin не создаёт платёж чужой брони → `404 NOT_FOUND`; владелец после отказа создаёт свой платёж | `pending_payment`, до первого платежа | Высокая | Покрыто | [test_admin_cannot_create_payment_for_another_users_booking](../tests/bookings/test_admin_booking_access.py) |
| ACC-005 | <a id="acc-005"></a>Admin не симулирует чужую оплату → `404 NOT_FOUND`, бронь и платёж неизменны | Успех и отказ × оба варианта `booking_with_payment` | Высокая | Покрыто | [test_admin_cannot_simulate_success_of_another_users_payment](../tests/bookings/test_admin_booking_access.py), [test_admin_cannot_simulate_failure_of_another_users_payment](../tests/bookings/test_admin_booking_access.py) |
| ACC-006 | <a id="acc-006"></a>Создание брони требует авторизации → `401 UNAUTHORIZED`; даты и ключ не заняты, авторизованный повтор → `201` | `no_header`, `empty_bearer` | Высокая | Покрыто | [test_create_booking_requires_authorization](../tests/bookings/test_booking_payment_authorization.py) |
| ACC-007 | <a id="acc-007"></a>Создание платежа требует авторизации → `401 UNAUTHORIZED`; бронь неизменна, владелец затем создаёт платёж | `no_header`, `empty_bearer`; бронь без платежа | Высокая | Покрыто | [test_create_payment_requires_authorization](../tests/bookings/test_booking_payment_authorization.py) |
| ACC-008 | <a id="acc-008"></a>Чтение и симуляция оплаты требуют авторизации → `401 UNAUTHORIZED`, ресурсы неизменны | `no_header`, `empty_bearer` × `operation=read_booking` / `read_payment` / `success` / `failure`; `pending_payment` / `pending` | Высокая | Покрыто | [test_existing_booking_and_payment_require_authorization](../tests/bookings/test_booking_payment_authorization.py) |
| ACC-009 | <a id="acc-009"></a>Список броней отклоняет неверные учётные данные → `401 UNAUTHORIZED`, доступ действующего пользователя к профилю сохраняется | `operation=bookings`; `token_kind=missing` / `empty` / `malformed` / `invalid_signature` | Высокая | Покрыто | [test_protected_operations_reject_invalid_credentials](../tests/auth/test_authorization.py) |
| ACC-010 | <a id="acc-010"></a>Admin создаёт бронь только для себя → `201`, владелец равен текущему admin | Создание собственным admin-токеном | Высокая | Не покрыто | — |
| ACC-011 | <a id="acc-011"></a>Деактивация владельца не удаляет бронь и платёж, admin продолжает их читать → `200`, прежние данные | Отключённый владелец; `pending_payment` / `pending` | Высокая | Покрыто | [test_deactivation_preserves_booking_and_payment](../tests/users/test_admin_users.py) |
| ACC-012 | <a id="acc-012"></a>Admin отменяет бронь отключённого владельца по общим условиям → `200`, даты свободны, платёж отменён/возвращён | До заезда, pending_payment/pending и confirmed/succeeded; полный возврат для оплаченной брони | Высокая | Не покрыто | — |
| ACC-013 | <a id="acc-013"></a>Admin не создаёт и не симулирует оплату от имени отключённого владельца → `404 NOT_FOUND`, ресурсы сохранены | Создание платежа; симуляция успеха/отказа; существующая непросроченная бронь отключённого пользователя | Высокая | Не покрыто | — |
| ACC-014 | <a id="acc-014"></a>Реактивация восстанавливает доступ владельца к сохранённым броням и платежам | После отключения и включения прежний неистёкший JWT читает собственные ресурсы → `200`; состояние соответствует прошедшему времени, а не обязательно снимку до отключения | Высокая | Не покрыто | — |

Для ACC-006–009 также проверяется `WWW-Authenticate: Bearer`. ACC-009 без токена входит в `smoke`. Матрица не распространяет эти результаты на истёкший JWT или на все операции с повреждённой подписью.

<a id="admin-booking-access-checklist"></a>

Чтение чужих ресурсов admin описано в [RED-001](#red-001), доступ к списку — [LST-003–004](#lst-003). Отмена: [CAN-006](testing-booking-lifecycle.md#can-006) — разрешена admin; [CAN-007](testing-booking-lifecycle.md#can-007) — запрещена другому пользователю; [CAN-008](testing-booking-lifecycle.md#can-008) — требует авторизации.

<a id="booking-list"></a>

## Список и детали

### Список бронирований

Источники: FR-04, FR-10 и раздел «Бронирования» REST-спецификации. Фикстура `booking_catalog` создаёт четыре брони владельца в двух отелях и бронь другого пользователя. Вариант `reader=admin` для сортировки и страниц использует фильтр `user_id` тестового владельца.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| LST-001 | <a id="lst-001"></a>Фильтры статуса и отеля возвращают точный набор собственных броней, не раскрывая чужие | Владелец; `case=pending`, `confirmed`, `cancelled`, `expired`, `completed`, `first_hotel`, `second_hotel`; для expired/completed здесь пустая выдача | Высокая | Покрыто | [test_booking_list_filters](../tests/bookings/test_booking_list.py) |
| LST-002 | <a id="lst-002"></a>Обычный пользователь не применяет `user_id` → `403 FORBIDDEN`; без фильтра видит только свои брони | `target=self` / `other` / `unknown` | Высокая | Покрыто | [test_owner_cannot_filter_by_any_user_id](../tests/bookings/test_booking_list.py) |
| LST-003 | <a id="lst-003"></a>Admin объединяет фильтры владельца, отеля и статуса → `200`, только подходящая бронь | `user_id` + первый `hotel_id` + `status=pending_payment` | Высокая | Покрыто | [test_admin_filters_bookings_by_owner_hotel_and_status](../tests/bookings/test_booking_list.py) |
| LST-004 | <a id="lst-004"></a>Admin видит брони разных владельцев в выбранном отеле → `200`, точные ID и total | `hotel_id` без фильтра владельца; три подготовленные брони двух пользователей | Высокая | Покрыто | [test_admin_lists_both_owners_with_hotel_filter](../tests/bookings/test_booking_list.py) |
| LST-005 | <a id="lst-005"></a>Границы даты заезда включительны, сочетания фильтров применяются совместно | Владелец; `case=from`, `to`, `same_day`, `status_hotel`, `status_date` | Средняя | Покрыто | [test_booking_list_filters](../tests/bookings/test_booking_list.py) |
| LST-006 | <a id="lst-006"></a>Сортировка соответствует полю и направлению, при равенстве даты заезда/суммы — UUID по возрастанию | Владелец: default `-created_at`, ±`created_at`, ±`check_in`, ±`total_price`; admin: `-total_price`; default page 20/0 | Средняя | Покрыто | [test_booking_list_sorting](../tests/bookings/test_booking_list.py) |
| LST-007 | <a id="lst-007"></a>Страницы возвращают ожидаемые записи без потерь и дублей; total не зависит от страницы | `reader=owner` / `admin`; `(limit, offset)=(2,0), (2,2), (2,4), (1,0), (100,0)`; `sort=check_in` | Средняя | Покрыто | [test_booking_pages_have_no_missing_or_duplicate_records](../tests/bookings/test_booking_list.py) |
| LST-008 | <a id="lst-008"></a>Неверные query-параметры → `422 VALIDATION_ERROR` соответствующего поля | Admin; limit 0/101/`text`, offset −1, неизвестный status, неверные UUID hotel/user, неверные даты from/to | Средняя | Покрыто | [test_booking_list_rejects_invalid_query](../tests/bookings/test_booking_list.py) |
| LST-009 | <a id="lst-009"></a>Неверная сортировка → `422 INVALID_SORT`; обратный диапазон дат → `422 INVALID_FILTER_RANGE` | Владелец; `sort=unknown`, `--check_in`; from позже to | Средняя | Покрыто | [test_booking_list_rejects_invalid_sort_and_range](../tests/bookings/test_booking_list.py) |
| LST-010 | <a id="lst-010"></a>Разрешённый фильтр по отсутствующему ресурсу → `200`, пустые items и total=0 | Admin; `field=hotel_id` / `user_id`, случайный UUID | Средняя | Покрыто | [test_admin_filter_by_unknown_resource_is_empty](../tests/bookings/test_booking_list.py) |

Реальные истёкшие и завершённые брони в списках: [EXP-006](testing-booking-lifecycle.md#exp-006), [CMP-005](testing-booking-lifecycle.md#cmp-005). В LST-007 данные между запросами не меняются; поведение страниц при конкурентных изменениях не проверяется и контракт не обещает снимок списка.

<a id="booking-payment-reading"></a>

### Детали брони и платежа

Источники: FR-04, FR-07, FR-10, модели Booking/Payment и ошибки REST-спецификации. `readable_resources` в [test_booking_payment_reading.py](../tests/bookings/test_booking_payment_reading.py) готовит состояния через API; `pending` — пара `pending_payment` / `pending`, `confirmed` — `confirmed` / `succeeded`, `failed` — `pending_payment` / `failed`, `cancelled` — `cancelled` / `cancelled`, `refunded` — `cancelled` / `refunded`.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| RED-001 | <a id="red-001"></a>Владелец и admin читают ресурсы → `200`, сохранённые данные, схема и форматы верны; суммы и связь платежа с бронью согласованы, секретных полей нет | `readable_resources=pending` / `confirmed` / `failed` / `cancelled` / `refunded` × `reader=owner` / `admin` × `resource=booking` / `payment` | Высокая | Покрыто | [test_booking_and_payment_read_response_contract](../tests/bookings/test_booking_payment_reading.py) |
| RED-002 | <a id="red-002"></a>Отсутствующий ресурс → `404 NOT_FOUND` | `reader=owner` / `admin` × `resource=booking` / `payment`; случайный UUID | Средняя | Покрыто | [test_read_unknown_booking_or_payment](../tests/bookings/test_booking_payment_reading.py) |
| RED-003 | <a id="red-003"></a>Неверный UUID → `422 VALIDATION_ERROR` для соответствующего path-поля | Обычный пользователь; `resource=booking` / `payment`, `not-a-uuid` | Средняя | Покрыто | [test_read_booking_or_payment_rejects_invalid_uuid](../tests/bookings/test_booking_payment_reading.py) |
| RED-004 | <a id="red-004"></a>Admin читает завершённые ресурсы → `200`, бронь `completed`, платёж `succeeded` | Чужая завершённая бронь и её платёж | Высокая | Не покрыто | — |

Истёкшие ресурсы — [EXP-007](testing-booking-lifecycle.md#exp-007); завершённые ресурсы владельца и их история — [CMP-001–002](testing-booking-lifecycle.md#cmp-001). RED-001 также проверяет UTC для временных полей, `updated_at >= created_at`, `X-Request-ID` и отсутствие `password`, `password_hash`, `access_token`. Дополнительное чтение admin и сохранность ресурсов владельца проверяет [test_admin_can_read_another_users_booking_and_payment](../tests/bookings/test_admin_booking_access.py).

<a id="booking-payment-mutation-ids"></a>

### Идентификаторы платёжных операций

Источник: ошибки REST-спецификации. Идентификаторы чтения описаны в RED-002–003; отмены — в [CAN-012–013](testing-booking-lifecycle.md#can-012).

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| PID-001 | <a id="pid-001"></a>Платёжная операция с неверным UUID → `422 VALIDATION_ERROR` нужного path-поля; с отсутствующим ресурсом → `404 NOT_FOUND` | `operation=create_payment` / `simulate_success` / `simulate_failure` × `malformed_uuid` / `unknown_uuid` | Средняя | Покрыто | [test_booking_and_payment_mutations_reject_invalid_ids](../tests/bookings/test_booking_payment_ids.py) |

<a id="room-booking-integrity"></a>

## Изменение номера и отеля при действующей брони

Источники: [FR-03. Каталог](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-03-каталог), FR-05 (актуализация истечения) и ошибки REST-спецификации. Изменения выполняет admin, бронь и платёж читает владелец. `booking_with_payment` — пары `pending_payment` / `pending` и `confirmed` / `succeeded`; заезд в будущем.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| RMI-001 | <a id="rmi-001"></a>Вместимость нельзя снизить ниже числа гостей → `409 CAPACITY_IN_USE`, номер, бронь и платёж неизменны | 2 гостя, новая вместимость 1 × оба варианта `booking_with_payment` | Высокая | Покрыто | [test_capacity_cannot_be_reduced_below_existing_booking_guests](../tests/rooms/test_room_booking_integrity.py) |
| RMI-002 | <a id="rmi-002"></a>Номер с блокирующей бронью нельзя архивировать → `409 ACTIVE_BOOKINGS_EXIST`, номер, бронь и платёж неизменны | Оба варианта `booking_with_payment` | Высокая | Покрыто | [test_room_with_active_booking_cannot_be_archived](../tests/rooms/test_room_booking_integrity.py) |
| RMI-003 | <a id="rmi-003"></a>Отключение номера не мешает оплате уже созданной брони → `200`, бронь `confirmed`, платёж `succeeded`, срок и суммы прежние | `pending_payment` / `pending`, затем `is_available=false`; после оплаты номер остаётся отключённым | Высокая | Покрыто | [test_existing_booking_can_be_paid_after_room_is_disabled](../tests/rooms/test_room_booking_integrity.py) |
| RMI-004 | <a id="rmi-004"></a>Отель с блокирующей бронью номера нельзя архивировать → `409 ACTIVE_BOOKINGS_EXIST`, отель, номер, бронь и платёж неизменны | Оба варианта `booking_with_payment` | Высокая | Покрыто | [test_hotel_with_active_booking_cannot_be_archived](../tests/hotels/test_hotel_management.py) |
| RMI-005 | <a id="rmi-005"></a>Просроченное удержание актуализируется и не мешает архивированию → `204`, бронь `expired` | Номер / отель; `expires_at` в прошлом, иных блокирующих броней нет | Высокая | Не покрыто | — |
| RMI-006 | <a id="rmi-006"></a>Вместимость можно снизить до числа гостей без нарушения брони → `200`, бронь и платёж неизменны | Вместимость 3 → 2 при двух гостях × оба варианта `booking_with_payment` | Средняя | Не покрыто | — |
| RMI-007 | <a id="rmi-007"></a>Архивирование каталога не удаляет прежние брони, платежи и историю состояний | Номер/отель без блокирующих броней; cancelled/expired/completed, чтение владельцем/admin и сравнение истории в БД до/после | Высокая | Не покрыто | — |

Изменение цены — [BKG-011](#bkg-011); запрет новых броней отключённого номера — BKG-008. RMI-003 проверяет оплату существующего платежа после отключения, а не создание нового платежа. Для RMI-005 нужен контроль актуализации, чтобы worker не изменил состояние раньше проверяемой операции. Общая валидация изменений каталога описана в [testing-hotels.md](testing-hotels.md#room-management).

<a id="repeated-requests-checklist"></a>

## Идемпотентность бронирования

Источник: [FR-06. Идемпотентность](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-06-идемпотентность) и REST-спецификация версии из начала документа. Общие условия: собственная бронь, новый ключ, корректное тело; если не указано иное, состояние `pending_payment`. В повторе ожидается исходный снимок, актуальное состояние читается через GET.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| IDM-001 | <a id="idm-001"></a>Тот же ключ и валидное тело возвращают исходный `201`, снимок и `Location`, `Idempotency-Replayed: true`; бронь одна, данные и срок неизменны | Порядок JSON-полей изменён; исходный ответ имеет `Idempotency-Replayed: false` | Высокая | Частично: перестановка полей проверена; эквивалентные формы нормализуемых значений — нет | [test_same_key_and_body_replay_original_booking](../tests/bookings/test_booking_idempotency.py) |
| IDM-002 | <a id="idm-002"></a>Тот же ключ с другим валидным телом → `409 IDEMPOTENCY_KEY_REUSED`, независимо от состояния; исходная бронь сохранена, дубля нет | `guests: 2 → 1`; проверено только `pending_payment` | Высокая | Частично: конфликт после оплаты, отмены, истечения и завершения не проверен | [test_same_key_with_different_body_is_rejected](../tests/bookings/test_booking_idempotency.py) |
| IDM-003 | <a id="idm-003"></a>Валидация выполняется до replay → неверное тело получает `422 VALIDATION_ERROR`; исходный корректный повтор по-прежнему возвращает снимок | Сохранённый ключ; `guests=0`, ошибка `body.guests`; затем исходное тело | Высокая | Покрыто | [test_invalid_body_is_rejected_before_replay](../tests/bookings/test_booking_idempotency.py) |
| IDM-004 | <a id="idm-004"></a>Ключи независимы между пользователями: один ключ создаёт разные брони, каждый повтор получает собственный снимок | Два пользователя, один номер, смежные непересекающиеся даты; разные ID, у каждого одна бронь | Высокая | Покрыто | [test_idempotency_key_is_scoped_to_user](../tests/bookings/test_booking_validation.py) |
| IDM-005 | <a id="idm-005"></a>Повтор после отмены возвращает исходный `201`, но не восстанавливает бронь и не занимает даты | `cancelled` без платежа; прежний `Location`, `Idempotency-Replayed: true`, GET остаётся `cancelled`, в списке одна бронь | Высокая | Покрыто | [test_replay_after_cancellation_does_not_create_new_booking](../tests/bookings/test_booking_idempotency.py) |
| IDM-006 | <a id="idm-006"></a>Повтор после оплаты возвращает исходный `201`, не меняет подтверждённую бронь и успешный платёж | `confirmed` / `succeeded`; прежние срок и `Location`, `Idempotency-Replayed: true`, дубля нет | Высокая | Покрыто | [test_replay_after_payment_preserves_confirmed_booking](../tests/bookings/test_booking_idempotency.py) |
| IDM-007 | <a id="idm-007"></a>Отключённый владелец не получает сохранённый ответ → `401 UNAUTHORIZED` | Успешный исходный запрос, затем деактивация, повтор с прежними JWT, ключом и телом | Высокая | Не покрыто | — |
| IDM-008 | <a id="idm-008"></a>Бизнес-отказ не занимает ключ; после устранения причины первая успешная операция с тем же ключом → `201`, `Idempotency-Replayed: false` | Отказ `ROOM_NOT_AVAILABLE`, затем повтор после освобождения дат | Высокая | Не покрыто | — |
| IDM-009 | <a id="idm-009"></a>Допустимый ключ принимается → `201`, первый ответ не replay, повтор возвращает тот же снимок | `min` — 1 символ; `max` — 128; `allowed_characters` — `Az09._:-` | Средняя | Покрыто | [test_booking_accepts_valid_idempotency_key](../tests/bookings/test_booking_validation.py) |
| IDM-010 | <a id="idm-010"></a>Отсутствующий/невалидный ключ → `422 VALIDATION_ERROR`, бронь не создаётся, даты свободны | `missing`, `empty`, `too_long` (129), `space`, `slash`, `punctuation` (`a!`), `at` (`a@b`) | Средняя | Покрыто | [test_booking_rejects_invalid_idempotency_key](../tests/bookings/test_booking_validation.py) |
| IDM-011 | <a id="idm-011"></a>Бронь, ключ, хеш и исходный снимок сохраняются атомарно | Управляемый сбой между сохранениями: нет частичной брони/занятого ключа; повтор с тем же ключом после устранения сбоя создаёт одну бронь | Высокая | Не покрыто | — |
| IDM-012 | <a id="idm-012"></a>Ключ успешной операции не истекает до сброса БД | Поздний повтор и повтор после перезапуска API с той же БД → исходный `201`, тот же снимок, replay=true, без дубля; конечный набор задержек не доказывает отсутствие любого TTL | Высокая | Не покрыто | — |
| IDM-013 | <a id="idm-013"></a>После отмены/истечения новая бронь владельца требует нового ключа | Тот же пользователь, номер и даты ещё допустимы: старый ключ возвращает снимок, новый создаёт новый ID и срок; исходная бронь остаётся терминальной | Высокая | Не покрыто | — |

Повторы после истечения — [EXP-005](testing-booking-lifecycle.md#exp-005), после завершения — [CMP-004](testing-booking-lifecycle.md#cmp-004); одновременные запросы с одним ключом — [CON-002](#con-002). Ключ после отказа схемы/JSON — [BKG-012 и BKG-015](#bkg-012), после отсутствующей авторизации — [ACC-006](#acc-006).

## Конкурентные запросы

Источники: [FR-09. Конкуренция](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-09-конкуренция), FR-06 (ключи) и FR-07 (платёжные состояния). Общие условия реализованных проверок: выделенные тестовые данные, будущий заезд, неистёкшее удержание; два потока отправляют запросы после общего `Barrier(2)`.


| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| CON-001 | <a id="con-001"></a><a id="booking-concurrency"></a>Два запроса бронирования пересекающихся дат создают одну бронь: `201` и `409 ROOM_NOT_AVAILABLE`; номер занят | Два пользователя, разные ключи, один номер и совпадающие даты; списки обоих пользователей и admin, GET победителя | Высокая | Покрыто | [test_only_one_concurrent_booking_can_reserve_room](../tests/bookings/test_booking_concurrency.py) |
| CON-002 | <a id="con-002"></a><a id="concurrent-idempotency"></a>Одинаковые ключ и тело создают одну бронь: оба `201`, одинаковые снимки и `Location`, ровно один replay | Один пользователь; `Idempotency-Replayed: false/true`; последующий replay, GET и списки владельца/admin сохраняют одну бронь и срок | Высокая | Покрыто | [test_concurrent_same_key_returns_one_booking](../tests/bookings/test_booking_concurrency.py) |
| CON-003 | <a id="con-003"></a><a id="payment-concurrency"></a>Одновременно создаётся только один `pending`-платёж: `201` и `409 PAYMENT_ALREADY_PENDING`, бронь неизменна | Одна бронь без платежа; сумма и валюта из брони; SQL подтверждает ровно одну запись; `db` | Высокая | Покрыто | [test_only_one_concurrent_payment_is_created](../tests/payments/test_payment_concurrency.py) |
| CON-004 | <a id="con-004"></a><a id="payment-success-concurrency"></a>Одновременный успех применяется один раз: `200` и `409 BOOKING_NOT_PAYABLE`, итог `confirmed` / `succeeded` | Один `pending`-платёж; SQL подтверждает одну запись и по одному переходу брони/платежа, без лишних событий; `db` | Высокая | Покрыто | [test_concurrent_payment_success_is_applied_only_once](../tests/payments/test_payment_concurrency.py) |
| CON-006 | <a id="con-006"></a>Первая симуляция определяет результат, вторая получает `409`: после успеха `BOOKING_NOT_PAYABLE`, после отказа `PAYMENT_STATE_CONFLICT`; лишних переходов нет | Два отказа; успех против отказа одного `pending`-платежа | Высокая | Не покрыто | — |
| CON-007 | <a id="con-007"></a>Тайм-аут блокировки, deadlock или конфликт сериализации → `409 CONCURRENT_OPERATION`, изменения откатываются, запрос можно повторить | Предел ожидания блокировки 10 с, SQL 30 с; при создании повтор с тем же ключом | Высокая | Не покрыто | — |
| CON-008 | <a id="con-008"></a>Один ключ с разными валидными телами создаёт одну бронь: `201` и `409 IDEMPOTENCY_KEY_REUSED`, без дубля | Один пользователь, конкурентные запросы с различным числом гостей; следствие FR-06 и FR-09 | Высокая | Не покрыто | — |

В CON-001–002 сохранённые брони проверяются через API, в CON-003–004 платежи и история дополнительно читаются через [db.py](../db.py). «Покрыто» относится к перечисленным запросам и результатам: барьер сближает отправку, но не доказывает пересечение серверных транзакций и не задаёт порядок блокировок. Для CON-007 нужен управляемый сбой/ожидание в БД.

<a id="payment-cancellation-concurrency"></a>

**CON-005** — ссылка на [CAN-014](testing-booking-lifecycle.md#can-014): оплата против отмены, обе ветви и ограничение их перебора. Две отмены — [CAN-015](testing-booking-lifecycle.md#can-015); оплата против истечения и момент получения блокировки — [EXP-008–010](testing-booking-lifecycle.md#exp-008).
