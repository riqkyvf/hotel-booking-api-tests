# Оплата и жизненный цикл бронирования

Контракт API: [REST-спецификация](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/api-specification.md) и [требования](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md) версии из [CI](../.github/workflows/api-tests.yml). Локальные пояснения: [модель бизнес-правил](business-rules.md).

Сценарии с меткой `db` используют PostgreSQL для подготовки дат и проверки сохранённых состояний. Статусы меняет приложение. [Настройки подключения](../README.md#быстрый-старт) · [Как читать каталог](README.md#check-catalog).

**Разделы:** [платежи](#payment-failure-checklist) · [отмена](#cancellation-details) · [истечение](#booking-expiration-checklist) · [завершение](#booking-completion).

Создание, права доступа, чтение, идемпотентность и конкуренция — в [матрице бронирований](testing-bookings.md).

<a id="payment-failure-checklist"></a>

## Платежи

Источники: [FR-07. Тестовые платежи](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-07-тестовые-платежи) и [REST-спецификация платежей](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/api-specification.md#тестовые-платежи). Общие условия: запросы владельца, бронь `pending_payment`, удержание не истекло; перед симуляцией платёж `pending`, кроме явно указанных вариантов. Внешних списаний нет: проверяется тестовая модель оплаты.

<a id="booking-payment-gaps"></a>

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| PAY-001 | <a id="pay-001"></a>Создание платежа → `201`, UUID, `pending`, сумма и валюта из брони, `failure_reason=null`; GET сохраняет результат | Бронь без платежа; `1234.56 × 3 = 3703.68 RUB`; `smoke` | Высокая | Покрыто | [test_user_can_pay_for_booking](../tests/bookings/test_booking_flow.py) |
| PAY-002 | <a id="pay-002"></a>Успех атомарно переводит платёж в `succeeded`, бронь в `confirmed`; суммы и связи сохранены | Симуляция успеха → `200`, затем GET обоих ресурсов; `smoke` | Высокая | Частично: конечные состояния проверены, откат при внутреннем сбое — нет | [test_user_can_pay_for_booking](../tests/bookings/test_booking_flow.py) |
| PAY-003 | <a id="pay-003"></a>Отказ → `200`, платёж `failed` с причиной; бронь остаётся `pending_payment`, срок и сумма прежние, номер занят | `custom_reason`; `default_reason` — тело `{}`, причина `Simulated decline` | Высокая | Покрыто | [test_payment_failure_preserves_booking_and_room_hold](../tests/payments/test_payment_failure.py) |
| PAY-004 | <a id="pay-004"></a>После каждого отказа разрешён новый платёж с новым ID без ограничения числа последовательных попыток и без продления срока; он может успешно подтвердить бронь, старый `failed` неизменен | Одна неудачная попытка, новая `pending`, затем успех; сумма и валюта прежние | Высокая | Частично: проверена одна неудачная попытка, длинная последовательность отказов — нет | [test_user_can_pay_with_new_payment_after_failure](../tests/payments/test_payment_failure.py) |
| PAY-005 | <a id="pay-005"></a>Повторное создание при существующем `pending` → `409 PAYMENT_ALREADY_PENDING`, снимки брони и платежа неизменны | Последовательный повтор создания платежа | Высокая | Покрыто | [test_second_pending_payment_is_rejected](../tests/payments/test_payment_repeated_requests.py) |
| PAY-006 | <a id="pay-006"></a>Для `confirmed` и `cancelled` платёжные операции → `409 BOOKING_NOT_PAYABLE`, ресурсы неизменны | `non_payable_booking=confirmed` / `cancelled` × `operation=create_payment` / `success` / `failure` | Высокая | Покрыто | [test_non_payable_booking_rejects_payment_operations](../tests/bookings/test_booking_payment_states.py) |
| PAY-007 | <a id="pay-007"></a>Повтор отказа для `failed` → `409 PAYMENT_STATE_CONFLICT`, исходная причина и бронь не меняются | После отказа с собственной причиной повтор с `{}`; бронь ещё ожидает оплаты | Высокая | Покрыто | [test_repeated_payment_failure_preserves_original_reason](../tests/payments/test_payment_repeated_requests.py) |
| PAY-008 | <a id="pay-008"></a>Успешная симуляция уже отказанного платежа запрещена → `409 PAYMENT_STATE_CONFLICT`, ресурсы неизменны | Платёж `failed`, бронь ещё `pending_payment`, срок не истёк | Высокая | Не покрыто | — |
| PAY-009 | <a id="pay-009"></a>Причина отказа длиной 1–250 принимается → `200`, сохраняется в `failed`; бронь неизменна | `min_length` — 1 символ, `max_length` — 250 | Средняя | Покрыто | [test_payment_failure_accepts_reason_boundaries](../tests/payments/test_payment_validation.py) |
| PAY-010 | <a id="pay-010"></a>Неверная причина и лишние поля → `422 VALIDATION_ERROR` нужного поля, ресурсы неизменны | reason: пустая строка, 251 символ, `null`, число, boolean, массив, объект; лишние `unexpected`, `status`, `amount` | Средняя | Покрыто | [test_payment_failure_rejects_invalid_fields](../tests/payments/test_payment_validation.py) |
| PAY-011 | <a id="pay-011"></a>Некорректное JSON-тело отказа → `422 VALIDATION_ERROR`, ресурсы неизменны | `malformed_json`, `array` | Средняя | Покрыто | [test_payment_failure_rejects_invalid_json_body](../tests/payments/test_payment_validation.py) |
| PAY-012 | <a id="pay-012"></a>Для отказа обязателен JSON-объект, отсутствие тела и JSON `null` → `422 VALIDATION_ERROR`, ресурсы неизменны | Запрос без тела; тело `null` (в отличие от допустимого `{}`) | Средняя | Не покрыто | — |

Причины и варианты отказа: [data/payments.py](../data/payments.py). PAY-005 не считает все записи платежей в БД; проверка их единственности при конкурентном создании — [CON-003](testing-bookings.md#con-003). Дополнительный последовательный повтор успеха проверяет [test_repeated_payment_success_is_rejected](../tests/payments/test_payment_repeated_requests.py); это вариант правила PAY-006.

Связанные проверки: [ACC-002–008](testing-bookings.md#acc-002) — права и авторизация; [RED-001](testing-bookings.md#red-001) — чтение и схема; [PID-001](testing-bookings.md#pid-001) — идентификаторы; [CAN-002–004](#can-002) — отмена/возврат платежа; [EXP-001 и EXP-004](#exp-001) — истечение; [CMP-003](#cmp-003) — завершение; [CON-003–005](testing-bookings.md#con-003) — конкурентные операции.

<a id="booking-cancellation-checklist"></a>

<a id="cancellation-details"></a>

## Отмена

Источники: FR-08 (отмена), FR-09 (конкуренция), FR-04 (чужие ресурсы) и REST-спецификация версии из начала документа. Если не указано иное, заезд в будущем по UTC, удержание не истекло, запрос выполняет владелец.


| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| CAN-001 | <a id="can-001"></a>Отмена → `200`, бронь `cancelled`, даты освобождены для другого пользователя | `pending_payment`, без платежа (`without_payment`) | Высокая | Покрыто | [test_cancellation_releases_room_for_another_user](../tests/bookings/test_booking_cancellation.py) |
| CAN-002 | <a id="can-002"></a>Отмена → `200`, бронь и ожидающий платёж `cancelled`, даты освобождены | Платёж `pending` (`pending_payment`) | Высокая | Покрыто | [test_cancellation_releases_room_for_another_user](../tests/bookings/test_booking_cancellation.py) |
| CAN-003 | <a id="can-003"></a>Отмена → `200`, бронь `cancelled`, полный возврат `refunded`, даты освобождены | Бронь `confirmed`, платёж `succeeded` (`paid_booking`) | Высокая | Покрыто | [test_cancellation_releases_room_for_another_user](../tests/bookings/test_booking_cancellation.py) |
| CAN-004 | <a id="can-004"></a>Отмена сохраняет отказ первого платежа и отменяет ожидающую повторную попытку | Первый платёж `failed`, второй `pending` | Высокая | Покрыто | [test_cancellation_preserves_failed_payment_and_cancels_pending_retry](../tests/bookings/test_booking_cancellation.py) |
| CAN-005 | <a id="can-005"></a>Повтор отмены → `200`, ресурсы неизменны, повторного возврата нет | До заезда: `without_payment`, `pending_payment`, `paid_booking` | Высокая | Частично: HTTP-снимки проверены, события возврата в БД — нет | [test_repeated_cancellation_preserves_booking_and_payment](../tests/bookings/test_booking_cancellation.py) |
| CAN-006 | <a id="can-006"></a>Admin может отменить чужую бронь → `200`, платёж отменяется/возвращается, даты свободны | `booking_with_payment=pending_payment` / `confirmed` | Высокая | Покрыто | [test_admin_can_cancel_another_users_booking](../tests/bookings/test_admin_booking_access.py) |
| CAN-007 | <a id="can-007"></a>Чужой пользователь не может отменить бронь → `404 NOT_FOUND`, ресурсы и занятость дат неизменны | `booking_with_payment=pending_payment` / `confirmed` | Высокая | Покрыто | [test_user_cannot_cancel_another_users_booking](../tests/bookings/test_booking_access.py) |
| CAN-008 | <a id="can-008"></a>Без авторизации отмена запрещена → `401 UNAUTHORIZED`, ресурсы неизменны | `operation=cancel_booking`; `no_header`, `empty_bearer` | Высокая | Покрыто | [test_existing_booking_and_payment_require_authorization](../tests/bookings/test_booking_payment_authorization.py) |
| CAN-009 | <a id="can-009"></a>В день заезда отмена запрещена → `409 CANCELLATION_CLOSED`, ресурсы и занятость дат неизменны | Владелец; `booking_status=pending_payment` / `confirmed`; бронь создана сегодня | Высокая | Покрыто | [test_cancellation_on_check_in_day_is_rejected](../tests/bookings/test_booking_cancellation.py) |
| CAN-010 | <a id="can-010"></a>Отмена `expired` запрещена → `409 BOOKING_STATE_CONFLICT`, ресурсы неизменны | `non_payable_booking=expired`; `db` | Высокая | Покрыто | [test_expired_booking_cannot_be_cancelled](../tests/bookings/test_booking_payment_states.py) |
| CAN-011 | <a id="can-011"></a>Отмена `completed` запрещена → `409 BOOKING_STATE_CONFLICT`, ресурсы и история неизменны | `operation=cancel`; `db` | Высокая | Покрыто | [test_completed_booking_rejects_changes](../tests/bookings/test_booking_completion.py) |
| CAN-012 | <a id="can-012"></a>Невалидный UUID → `422 VALIDATION_ERROR` для `path.booking_id` | `cancel_booking`, `malformed_uuid` | Средняя | Покрыто | [test_booking_and_payment_mutations_reject_invalid_ids](../tests/bookings/test_booking_payment_ids.py) |
| CAN-013 | <a id="can-013"></a>Отсутствующая бронь → `404 NOT_FOUND` | `cancel_booking`, `unknown_uuid` | Средняя | Покрыто | [test_booking_and_payment_mutations_reject_invalid_ids](../tests/bookings/test_booking_payment_ids.py) |
| CAN-014 | <a id="can-014"></a><a id="cancellation-race"></a>При гонке оплаты и отмены бронь отменена, платёж один, даты свободны, история согласована | Оплата первая: оба `200`, платёж `refunded`; отмена первая: оплата `409 BOOKING_NOT_PAYABLE`, платёж `cancelled`; `db` | Высокая | Частично: проверяется случившаяся ветвь, обе не гарантированы | [test_concurrent_payment_and_cancellation_have_consistent_result](../tests/payments/test_payment_concurrency.py) |
| CAN-015 | <a id="can-015"></a>Две конкурентные отмены → оба ответа `200`, единственный возврат | Оплаченная бронь до заезда | Высокая | Не покрыто | — |
| CAN-016 | <a id="can-016"></a>Повтор отмены после даты заезда → `200`, без нового возврата | Ранее отменённая бронь, дата заезда уже наступила | Высокая | Не покрыто | — |
| CAN-017 | <a id="can-017"></a>Ограничение даты отмены действует и для admin → `409 CANCELLATION_CLOSED`, ресурсы неизменны | Admin в день заезда; владелец и admin после заезда до выезда; действующая бронь | Высокая | Не покрыто | — |
| CAN-018 | <a id="can-018"></a>Отмена атомарна: внутренний сбой не оставляет частичных изменений | Управляемый сбой между изменениями брони и платежа | Высокая | Не покрыто | — |

CAN-001–003 входят в `smoke`. Варианты платежей заданы в [data/booking.py](../data/booking.py), `booking_with_payment` — в [conftest.py](../tests/conftest.py). CAN-014 соответствует [CON-005](testing-bookings.md#payment-cancellation-concurrency); история проверяет единственные переходы в отмену/возврат. CAN-018 требует управляемого сбоя на отдельном стенде или теста приложения.

Вне этой матрицы: отключённый владелец, невалидные/истёкшие JWT. Повтор создания после отмены — в разделе [идемпотентности](testing-bookings.md#repeated-requests-checklist).

<a id="booking-expiration-checklist"></a>

## Истечение удержания

Источники: FR-05 (истечение), FR-06 (повтор создания), FR-07 (оплата), FR-09 (блокировки). Общие условия реализованных проверок: SQL сдвигает `expires_at` собственной `pending_payment`-брони в прошлое; все варианты имеют метку `db`.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| EXP-001 | <a id="exp-001"></a>После срока оплата запрещена → `409 BOOKING_EXPIRED`, бронь `expired`, платёж `cancelled` | Симуляция успеха после сдвига срока; суммы и бизнес-поля сохранены | Высокая | Покрыто | [test_expired_booking_cancels_payment_and_releases_room](../tests/bookings/test_booking_expiration.py) |
| EXP-002 | <a id="exp-002"></a>Истечение освобождает номер для новой брони | Другой пользователь, те же номер и даты → `201`; исходная бронь остаётся `expired` | Высокая | Покрыто | [test_expired_booking_cancels_payment_and_releases_room](../tests/bookings/test_booking_expiration.py) |
| EXP-003 | <a id="exp-003"></a>Запрос доступности после срока возвращает свободные даты; ресурсы `expired` / `cancelled` | Первым после сдвига срока запрашивается доступность; бизнес-поля сохранены | Высокая | Покрыто | [test_availability_releases_expired_hold](../tests/rooms/test_room_availability.py) |
| EXP-004 | <a id="exp-004"></a>Операции оплаты для `expired` → `409 BOOKING_EXPIRED`, ресурсы неизменны | `non_payable_booking=expired`; `operation=create_payment` / `success` / `failure` | Высокая | Покрыто | [test_non_payable_booking_rejects_payment_operations](../tests/bookings/test_booking_payment_states.py) |
| EXP-005 | <a id="exp-005"></a>Повтор создания возвращает исходный `201`, не продлевает срок и не создаёт дубль | Исходные ключ и тело; прежний `Location`, `Idempotency-Replayed: true`; GET остаётся `expired` | Высокая | Покрыто | [test_replay_after_expiration_preserves_expired_booking](../tests/bookings/test_booking_idempotency.py) |
| EXP-006 | <a id="exp-006"></a>Фильтр `status=expired` возвращает истёкшую бронь со сроком из БД | `reader=owner` / `admin`; GET совпадает с элементом списка | Средняя | Покрыто | [test_booking_list_returns_expired_booking](../tests/bookings/test_booking_list.py) |
| EXP-007 | <a id="exp-007"></a>Детали истёкших ресурсов соответствуют схеме и сохранённым данным, не содержат секретов | `readable_resources=expired`; `reader=owner` / `admin` × `resource=booking` / `payment` | Средняя | Покрыто | [test_booking_and_payment_read_response_contract](../tests/bookings/test_booking_payment_reading.py) |
| EXP-008 | <a id="exp-008"></a>Удержание действует строго до срока: до него оплата разрешена, при равенстве — `BOOKING_EXPIRED` | Точная граница `decision_time < expires_at` и `decision_time = expires_at` | Высокая | Не покрыто | — |
| EXP-009 | <a id="exp-009"></a>Время отправки не продлевает удержание → `409 BOOKING_EXPIRED` | Запрос отправлен до срока, блокировка получена после | Высокая | Не покрыто | — |
| EXP-010 | <a id="exp-010"></a>Оплата, прошедшая проверку до срока, остаётся успешной после срока | Проверка под блокировкой до `expires_at`, завершение после; `confirmed` / `succeeded` | Высокая | Не покрыто | — |
| EXP-011 | <a id="exp-011"></a>Задержка worker не мешает освобождению номера и не разрешает оплату | Worker остановлен; актуализация запросом | Высокая | Не покрыто | — |
| EXP-012 | <a id="exp-012"></a>Worker самостоятельно актуализирует просроченные удержания и завершившиеся проживания | Без HTTP-запросов, способных актуализировать данные: БД показывает expired/cancelled либо completed/succeeded; ориентир цикла около 5 секунд, не строгий SLA завершения за 5 секунд | Высокая | Не покрыто | — |

Отмена истёкшей брони — CAN-010. В EXP-001, EXP-003 и EXP-006 worker может выполнить переход раньше запроса: покрыт конечный результат, механизм перехода не изолирован. EXP-008–010 требуют управления моментом решения и блокировками; сдвиг срока на минуту их не проверяет. Автономная работа worker — EXP-012. Каждый способ актуализации отдельно не изолирован: EXP-001/003/006 и CMP-001 подтверждают итоговое состояние, RMI-005 описывает непокрытое архивирование после срока.

<a id="booking-completion"></a>

## Завершение проживания

Источники: FR-05 (UTC-дата выезда), FR-06 (повтор создания), FR-07 (оплата), FR-08 (отмена). Общие условия реализованных проверок: оплаченная бронь, SQL переносит выезд на текущую UTC-дату с сохранением числа ночей и цены. Запросы выполняет владелец; метка `db`.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| CMP-001 | <a id="cmp-001"></a>В день выезда бронь становится `completed`, платёж остаётся `succeeded`; один системный переход, без новых событий платежа | Первое чтение: `reader=booking` / `payment` / `list` | Высокая | Покрыто | [test_confirmed_stay_completes_on_checkout_day](../tests/bookings/test_booking_completion.py) |
| CMP-002 | <a id="cmp-002"></a>Повторные чтения сохраняют ресурсы и не дублируют историю | После каждого из трёх вариантов `reader` повторяется проверка состояния | Высокая | Покрыто | [test_confirmed_stay_completes_on_checkout_day](../tests/bookings/test_booking_completion.py) |
| CMP-003 | <a id="cmp-003"></a>Оплата для `completed` → `409 BOOKING_NOT_PAYABLE`, ресурсы и история неизменны | `operation=create_payment` / `success` / `failure` | Высокая | Покрыто | [test_completed_booking_rejects_changes](../tests/bookings/test_booking_completion.py) |
| CMP-004 | <a id="cmp-004"></a>Повтор создания возвращает исходный `201` без дубля; актуальное состояние остаётся `completed` | Исходные ключ и тело; прежний `Location`, `Idempotency-Replayed: true`; платёж и история сохранены | Высокая | Покрыто | [test_idempotency_replay_preserves_completed_booking](../tests/bookings/test_booking_completion.py) |
| CMP-005 | <a id="cmp-005"></a>Фильтр `status=completed` возвращает завершённую бронь, GET подтверждает состояние | `reader=list`; ровно одна подготовленная запись | Средняя | Покрыто | [test_confirmed_stay_completes_on_checkout_day](../tests/bookings/test_booking_completion.py) |
| CMP-006 | <a id="cmp-006"></a>До UTC-даты выезда сохраняется `confirmed`, после полуночи — `completed`, независимо от часового пояса клиента | Переход через полночь UTC | Высокая | Не покрыто | — |
| CMP-007 | <a id="cmp-007"></a>Первое обращение позже даты выезда также завершает бронь единственным системным переходом, платёж остаётся `succeeded` | UTC-дата позже `check_out` | Высокая | Не покрыто | — |

Отмена завершённой брони — CAN-011. CMP-001–004 также проверяют схемы и сохранность бизнес-полей. Worker может завершить бронь раньше запроса; тесты не изолируют инициатор перехода.
