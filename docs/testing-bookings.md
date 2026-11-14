# Бронирование и платежи

Контракт API: [REST-спецификация](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/api-specification.md#бронирования) и [требования](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md) версии из [CI](../.github/workflows/api-tests.yml). Локальные пояснения: [модель бизнес-правил](business-rules.md).

Сценарии с меткой `db` используют PostgreSQL для подготовки дат и проверки сохранённых состояний. Статусы меняет приложение. [Настройки подключения](../README.md#быстрый-старт) · [Как читать каталог](README.md#check-catalog).

<a id="booking-payment-checklist"></a>

## Основной путь

[Основной путь](../tests/bookings/test_booking_flow.py) проверяет выбор доступного номера, создание и чтение брони, расчёт суммы и успешную оплату. Состояния после оплаты — `confirmed` и `succeeded`.

<a id="booking-restrictions-checklist"></a>

## Ограничения и доступность

[Ограничения](../tests/bookings/test_booking_restrictions.py) проверяют даты, вместимость и состояние номера при создании. [Валидация брони](../tests/bookings/test_booking_validation.py) проверяет типы, границы и ошибки JSON.

<a id="room-availability"></a>

[Доступность](../tests/rooms/test_room_availability.py) проверяет обязательные параметры, границы дат и числа гостей, расчёт стоимости, порядок причин отказа, архивный номер и освобождение интервала после истечения удержания. Запрос доступности сам не резервирует номер.

<a id="booking-overlap-checklist"></a>

[Пересечения](../tests/bookings/test_booking_overlap.py) проверяют запрет совпадающих и частично пересекающихся дат для `pending_payment` и `confirmed`. Соседние интервалы и бронь другого номера разрешены.

<a id="booking-access-checklist"></a>

## Доступ к броням и платежам

[Изоляция пользователей](../tests/bookings/test_booking_access.py) проверяет, что чужой пользователь не может прочитать бронь или платёж, отменить бронь или выполнить платёжную операцию.

<a id="admin-booking-access-checklist"></a>

[Права администратора](../tests/bookings/test_admin_booking_access.py) допускают чтение чужих ресурсов и отмену чужой брони. Создание и симуляция чужого платежа отклоняются.

<a id="booking-list"></a>

## Список и детали

[Список](../tests/bookings/test_booking_list.py) проверяет фильтры и их сочетания, сортировку, пагинацию и изоляцию владельцев. Обычный пользователь получает `403` с любым `user_id`, даже собственным. Для владельца и администратора проверяются две страницы и пустая выдача. Статусы `expired` и `completed` проверяются на бронях, прошедших соответствующий переход.

<a id="booking-payment-reading"></a>

[Детали брони и платежа](../tests/bookings/test_booking_payment_reading.py) проверяются для владельца и администратора в нескольких состояниях. Тесты валидируют JSON Schema и форматы, суммы и связь платежа с бронью.

<a id="booking-payment-mutation-ids"></a>

В запросах [чтения](../tests/bookings/test_booking_payment_reading.py) и [изменения](../tests/bookings/test_booking_payment_ids.py) различаются неверный формат UUID (`422 VALIDATION_ERROR`) и отсутствующая запись (`404 NOT_FOUND`); проверяются контракт ошибки и `X-Request-ID`.

<a id="booking-cancellation-checklist"></a>

## Отмена, истечение и завершение

<a id="cancellation-details"></a>

### Отмена: конкретные проверки

`PATCH /bookings/{booking_id}/cancel`: состояния брони и платежей, доступность номера, права и повторные запросы. [Как читать каталог](README.md#check-catalog).

#### Контракт и приоритеты

Контракт сверён с коммитом приложения `0d8396f38c8a7b727648585e33b3d34fe54652ab`, закреплённым в [CI](../.github/workflows/api-tests.yml), на 2026-11-14:

- **R08:** [FR-08. Отмена](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-08-отмена) — разрешённые состояния, UTC-дата, возврат, повтор и атомарность.
- **R09:** [FR-09. Конкуренция](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-09-конкуренция) — оплата против отмены и две отмены.
- **R04:** [FR-04. Бронирования](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-04-бронирования) — изоляция владельцев и блокирующие состояния.
- **API:** [REST-спецификация](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/api-specification.md) — операция без тела, роли, HTTP-коды и общий контракт ошибок.

**Высокий** — права, деньги, доступность номера и переходы состояний. **Средний** — ошибки идентификаторов.

Ошибки проверяются через [assert_api_error](../tests/assertions.py): HTTP-статус, схема, код и совпадение request ID тела и заголовка.

#### Успешная отмена и повтор

Источник CAN-001–005: R08. Заезд в будущем по UTC, удержание не истекло, запрос выполняет владелец. Варианты параметризации: [CANCELLATION_PAYMENT_CASES](../data/booking.py).

| ID | Приоритет | Проверка | Ожидаемый результат | Автотест и варианты |
| --- | --- | --- | --- | --- |
| CAN-001 | Высокий | Отменить `pending_payment` без платежа | `200`, бронь `cancelled`; GET возвращает сохранённый результат, даты доступны и другой пользователь создаёт бронь на тот же интервал; исходная бронь остаётся отменённой | [test_cancellation_releases_room_for_another_user](../tests/bookings/test_booking_cancellation.py), `without_payment` |
| CAN-002 | Высокий | Отменить бронь с платежом `pending` | `200`, бронь `cancelled`, платёж `cancelled`; даты доступны для новой брони, исходные ресурсы сохранены | [test_cancellation_releases_room_for_another_user](../tests/bookings/test_booking_cancellation.py), `pending_payment` |
| CAN-003 | Высокий | Отменить `confirmed` с платежом `succeeded` | `200`, бронь `cancelled`, платёж `refunded` на полную сумму; даты доступны для новой брони, исходные ресурсы сохранены | [test_cancellation_releases_room_for_another_user](../tests/bookings/test_booking_cancellation.py), `paid_booking` |
| CAN-004 | Высокий | После отказа первого платежа создать новый `pending`, затем отменить бронь | `200`, сохранённая бронь `cancelled`; первый платёж полностью сохраняет снимок `failed` с причиной, второй становится `cancelled` | [test_cancellation_preserves_failed_payment_and_cancels_pending_retry](../tests/bookings/test_booking_cancellation.py) |
| CAN-005 | Высокий | Повторно отменить уже отменённую бронь до заезда | Оба ответа `200`; повтор и GET сохраняют снимки брони и имеющегося платежа после первой отмены, номер доступен | [test_repeated_cancellation_preserves_booking_and_payment](../tests/bookings/test_booking_cancellation.py): `without_payment`, `pending_payment`, `paid_booking` |

CAN-001–003 входят в `smoke`: дополнительно проверяются новая бронь другого пользователя, сохранение отменённой брони и неизменность её владельца, номера, дат, гостей, цены и валюты. Существующий платёж сохраняет ID, связь с бронью, сумму и валюту.

Ограничения: CAN-004 не проверяет доступность номера; CAN-005 проверяет повтор по HTTP-снимкам, но не отсутствие повторных событий возврата в БД.

#### Права и ограничения состояний

Если не указано иное, заезд в будущем, удержание не истекло. В CAN-006–007 проверяются пары «бронь / платёж»: `pending_payment` / `pending` и `confirmed` / `succeeded` через [booking_with_payment](../tests/conftest.py). Источники: CAN-006–007 — R04, R08, API; CAN-008, CAN-012–013 — API; CAN-009–011 — R08.

| ID | Приоритет | Проверка | Ожидаемый результат | Автотест и варианты |
| --- | --- | --- | --- | --- |
| CAN-006 | Высокий | Admin отменяет чужую бронь в каждом из двух сочетаний | `200`, бронь `cancelled`, платёж соответственно `cancelled` / `refunded`; владелец читает сохранённые результаты, даты доступны | [test_admin_can_cancel_another_users_booking](../tests/bookings/test_admin_booking_access.py); оба варианта `booking_with_payment` |
| CAN-007 | Высокий | Другой обычный пользователь отменяет чужую бронь | `404 NOT_FOUND`; бронь и платёж совпадают с исходными снимками, даты остаются занятыми | [test_user_cannot_cancel_another_users_booking](../tests/bookings/test_booking_access.py); оба варианта `booking_with_payment` |
| CAN-008 | Высокий | Отменить существующую бронь без заголовка Authorization либо с пустым Bearer | `401 UNAUTHORIZED`, `WWW-Authenticate: Bearer`; бронь и платёж не изменяются | [test_existing_booking_and_payment_require_authorization](../tests/bookings/test_booking_payment_authorization.py); `operation=cancel_booking`, `no_header` / `empty_bearer` |
| CAN-009 | Высокий | Владелец отменяет бронь, созданную в день заезда по UTC | `409 CANCELLATION_CLOSED`; бронь и платёж неизменны, даты заняты | [test_cancellation_on_check_in_day_is_rejected](../tests/bookings/test_booking_cancellation.py); `booking_status=pending_payment` / `confirmed` |
| CAN-010 | Высокий | Отменить `expired` после актуализации срока | `409 BOOKING_STATE_CONFLICT`; снимки истёкшей брони и отменённого платежа не меняются | [test_expired_booking_cannot_be_cancelled](../tests/bookings/test_booking_payment_states.py); `non_payable_booking=expired`, `db` |
| CAN-011 | Высокий | Отменить `completed` после завершения проживания | `409 BOOKING_STATE_CONFLICT`; бронь остаётся `completed`, платёж `succeeded`, история не получает лишних переходов | [test_completed_booking_rejects_changes](../tests/bookings/test_booking_completion.py); `operation=cancel`, `db` |
| CAN-012 | Средний | Передать `booking_id=not-a-uuid` | `422 VALIDATION_ERROR`, ошибка поля `path.booking_id` | [test_booking_and_payment_mutations_reject_invalid_ids](../tests/bookings/test_booking_payment_ids.py); `cancel_booking`, `malformed_uuid` |
| CAN-013 | Средний | Передать корректный UUID отсутствующей брони | `404 NOT_FOUND` | [test_booking_and_payment_mutations_reject_invalid_ids](../tests/bookings/test_booking_payment_ids.py); `cancel_booking`, `unknown_uuid` |

<a id="cancellation-race"></a>

#### Конкуренция: CAN-014 / CON-005

**Приоритет: высокий. Источники: R08, R09, API.** Риск — несогласованное состояние брони и платежа при оплате одновременно с отменой. Автотест: [test_payment_concurrency.py](../tests/payments/test_payment_concurrency.py), `test_concurrent_payment_and_cancellation_have_consistent_result`, маркер `db`.

Предусловия: выделенный стенд и доступ к БД приложения. У владельца есть бронь `pending_payment` с будущим заездом и неистёкшим удержанием, один платёж `pending` на полную сумму. Сохранены исходные данные ресурсов.

| Шаг | Действие | Ожидаемый результат |
| --- | --- | --- |
| 1 | Проверить начальную историю брони и платежа | По одной записи создания: `pending_payment` и `pending`, автор — владелец |
| 2 | Токеном владельца одновременно отправить `POST /payments/{payment_id}/simulate-success` и `PATCH /bookings/{booking_id}/cancel` | Ответы соответствуют одной из двух ветвей ниже |
| 3 | Прочитать бронь, платёж и доступность дат | Бронь `cancelled`, совпадает с ответом отмены; платёж в состоянии выбранной ветви, сумма и валюта сохранены; `available=true`, `reason=null` |
| 4 | Проверить платежи брони и историю переходов | Существует ровно исходный платёж; после записей создания — только переходы выбранной ветви, автор — владелец |

| Порядок бизнес-операций | Ответ оплаты | Ответ отмены | Переходы брони после создания | Переходы платежа после создания |
| --- | --- | --- | --- | --- |
| Оплата первой | `200`, ответ содержит `succeeded` | `200` | `pending_payment → confirmed → cancelled` | `pending → succeeded → refunded` |
| Отмена первой | `409 BOOKING_NOT_PAYABLE` | `200` | `pending_payment → cancelled` | `pending → cancelled` |

Технически: два потока синхронизируются через `Barrier(2)`; история читается через `db.py`. Ветвь записывается в JUnit как `payment_cancellation_outcome`. Один запуск проверяет наблюдавшийся порядок обработки; повторные запуски не гарантируют покрытие обеих ветвей.

#### Непокрытые проверки

В просмотренных тестах не найдены проверки следующих требований. Их реализация пока не запланирована.

| ID | Приоритет | Требуемая проверка и ожидаемый результат | Источник | Что отсутствует |
| --- | --- | --- | --- | --- |
| CAN-015 | Высокий | Две конкурентные отмены оплаченной брони до заезда → оба ответа `200`, один возврат, единственные переходы в `cancelled` и `refunded` | R08, R09 | Отдельный конкурентный тест; CAN-005 проверяет последовательный повтор и только HTTP-снимки |
| CAN-016 | Высокий | Повторить отмену `cancelled` после наступления даты заезда → `200`, актуальный ресурс, без нового возврата | R08 | В CAN-005 заезд остаётся в будущем; нужна подготовка дат без прямой подмены статуса |
| CAN-017 | Высокий | Admin пытается отменить действующую бронь в день заезда; владелец и admin — после заезда, до выезда → `409 CANCELLATION_CLOSED`, ресурсы неизменны | R08 | CAN-009 покрывает владельца в день заезда, но не эти сочетания роли и даты |
| CAN-018 | Высокий | Сбой внутри отмены не оставляет частично отменённую бронь или платёж | R08 | Проверки успешных конечных состояний не доказывают атомарный откат; нужен управляемый сбой на отдельном стенде или тест уровня приложения |

Вне этого разбора: отмена администратором брони отключённого владельца и невалидные/истёкшие JWT. Повторное создание брони после отмены описано в разделе [идемпотентности](#repeated-requests-checklist).

<a id="booking-expiration-checklist"></a>

### Истечение удержания

Источники: [FR-05. Точное истечение](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-05-точное-истечение), FR-06 (повтор создания), FR-07 (запрет оплаты) и REST-спецификация указанной выше версии.

Общие условия: собственная бронь `pending_payment`; SQL сдвигает только её `expires_at` в прошлое. Все приведённые варианты имеют метку `db`. Высокий приоритет защищает оплату и освобождение номера; средний — чтение и поиск сохранённых ресурсов.

| ID | Приоритет | Проверка | Ожидаемый результат | Автотест и варианты |
| --- | --- | --- | --- | --- |
| EXP-001 | Высокий | Сдвинуть срок брони с платежом `pending` в прошлое, затем симулировать успешную оплату | `409 BOOKING_EXPIRED`; GET показывает бронь `expired` и платёж `cancelled`, суммы и остальные проверяемые бизнес-поля сохранены | [test_expired_booking_cancels_payment_and_releases_room](../tests/bookings/test_booking_expiration.py) |
| EXP-002 | Высокий | После истечения запросить доступность и создать бронь другого пользователя на те же номер и даты | `available=true`, `reason=null`; новая бронь получает `201`, свой ID и владельца; исходная бронь остаётся `expired` | [test_expired_booking_cancels_payment_and_releases_room](../tests/bookings/test_booking_expiration.py) |
| EXP-003 | Высокий | Сразу после сдвига срока запросить доступность занятого интервала | Даты становятся доступны; GET подтверждает `expired` / `cancelled`, срок совпадает с подготовленным, данные брони и платежа сохранены | [test_availability_releases_expired_hold](../tests/rooms/test_room_availability.py) |
| EXP-004 | Высокий | Для уже актуализированной `expired` выполнить создание платежа или симуляцию успеха/отказа | `409 BOOKING_EXPIRED`; снимки брони и платежа не меняются | [test_non_payable_booking_rejects_payment_operations](../tests/bookings/test_booking_payment_states.py); `non_payable_booking=expired`, `operation=create_payment` / `success` / `failure` |
| EXP-005 | Высокий | После истечения повторить создание с исходными ключом и телом | `201`, исходный снимок ответа, `Idempotency-Replayed: true`, прежний `Location`; GET остаётся `expired`, срок не продлён, в списке одна бронь | [test_replay_after_expiration_preserves_expired_booking](../tests/bookings/test_booking_idempotency.py) |
| EXP-006 | Средний | Получить список с `status=expired` владельцем и admin | `200`, список содержит только подготовленную истёкшую бронь; её ID, статус и срок верны, GET совпадает с элементом списка | [test_booking_list_returns_expired_booking](../tests/bookings/test_booking_list.py); `reader=owner` / `admin` |
| EXP-007 | Средний | Прочитать истёкшую бронь и отменённый платёж владельцем и admin | `200`, ответы совпадают с сохранёнными снимками, проходят схему и форматы; суммы и связь ресурсов верны, секретных полей нет | [test_booking_and_payment_read_response_contract](../tests/bookings/test_booking_payment_reading.py); `readable_resources=expired`, `reader=owner` / `admin`, `resource=booking` / `payment` |

Запрет отмены истёкшей брони описан в CAN-010. Ограничение EXP-001, EXP-003 и EXP-006: worker может актуализировать состояние раньше запроса; эти тесты подтверждают результат, но не изолируют механизм перехода.

#### Непокрытые проверки истечения

В просмотренном наборе не найдены следующие проверки FR-05 и FR-09; реализация не запланирована.

| ID | Приоритет | Проверка и ожидаемый результат |
| --- | --- | --- |
| EXP-008 | Высокий | При `decision_time < expires_at` оплата разрешена; при точном равенстве — `409 BOOKING_EXPIRED`, бронь `expired`, ожидающий платёж `cancelled` |
| EXP-009 | Высокий | Запрос оплаты отправлен до срока, но получил бизнес-блокировку после него → `409 BOOKING_EXPIRED`; время отправки не продлевает удержание |
| EXP-010 | Высокий | Оплата прошла проверку под блокировкой до срока, завершилась после него → успешный результат, бронь `confirmed`, платёж `succeeded` |
| EXP-011 | Высокий | При остановленном worker просроченная бронь актуализируется запросом и освобождает номер; оплата по-прежнему запрещена |

Для EXP-008–010 нужен управляемый момент решения и порядок блокировок; сдвиг срока на минуту в прошлое их не покрывает. Автономная работа worker и все способы запуска актуализации по отдельности здесь не проверены.

<a id="booking-completion"></a>

### Завершение проживания

Источники: FR-05 (завершение по UTC-дате), FR-06 (повтор создания), FR-07 (запрет оплаты), FR-08 (запрет отмены) и REST-спецификация версии из начала документа.

Общие условия: бронь оплачена через API; SQL переносит её выезд на текущую UTC-дату, сохраняя число ночей и цену. Проверки выполняются владельцем и имеют метку `db`. Высокий приоритет защищает состояние и оплаченные суммы; средний — чтение и фильтрацию.

| ID | Приоритет | Проверка | Ожидаемый результат | Автотест и варианты |
| --- | --- | --- | --- | --- |
| CMP-001 | Высокий | В день выезда прочитать бронь, платёж либо список завершённых броней | После запроса бронь `completed`, платёж остаётся исходным `succeeded`; в БД ровно один платёж, один системный переход `confirmed → completed`, без новых событий платежа | [test_confirmed_stay_completes_on_checkout_day](../tests/bookings/test_booking_completion.py); `reader=booking` / `payment` / `list` |
| CMP-002 | Высокий | Повторно прочитать завершённые ресурсы | Бронь и платёж сохраняют результат, дополнительных событий истории нет | [test_confirmed_stay_completes_on_checkout_day](../tests/bookings/test_booking_completion.py); все три варианта `reader` |
| CMP-003 | Высокий | Для `completed` создать платёж или симулировать успех/отказ | `409 BOOKING_NOT_PAYABLE`; бронь, платёж и история не меняются | [test_completed_booking_rejects_changes](../tests/bookings/test_booking_completion.py); `operation=create_payment` / `success` / `failure` |
| CMP-004 | Высокий | Повторить создание завершённой брони с исходными ключом и телом | `201`, исходный снимок, `Idempotency-Replayed: true`, прежний `Location`; актуальная бронь остаётся `completed`, в списке одна запись, платёж и история сохранены | [test_idempotency_replay_preserves_completed_booking](../tests/bookings/test_booking_completion.py) |
| CMP-005 | Средний | Запросить список с `status=completed` в день выезда | `200`, ровно одна запись с ID подготовленной брони; последующий GET подтверждает `completed` | [test_confirmed_stay_completes_on_checkout_day](../tests/bookings/test_booking_completion.py); `reader=list` |

Запрет отмены завершённой брони описан в CAN-011. CMP-001–004 также проверяют схему сохранённых ресурсов; завершение не меняет цену, сумму и остальные бизнес-поля подготовленной брони. Как и при истечении, тесты не отделяют переход по запросу от перехода worker.

#### Непокрытые проверки завершения

В просмотренном наборе не найдены следующие проверки FR-05; реализация не запланирована.

| ID | Приоритет | Проверка и ожидаемый результат |
| --- | --- | --- |
| CMP-006 | Высокий | До UTC-даты выезда бронь сохраняет `confirmed`; после перехода через полночь UTC становится `completed` независимо от локального часового пояса клиента |
| CMP-007 | Высокий | Первое обращение позже даты выезда также переводит `confirmed` в `completed` с единственным системным событием; платёж остаётся `succeeded` |

Подготовка выезда на сегодня проверяет равенство дат, но не переход через полночь и не отдельный случай пропущенной даты выезда.

<a id="room-booking-integrity"></a>

## Изменение номера при действующей брони

[Целостность брони](../tests/rooms/test_room_booking_integrity.py) проверяет запрет архивации и снижения вместимости ниже числа гостей. Изменение цены действует на новые брони, а прежняя хранит исходную сумму. Отключение номера не мешает оплатить уже созданную бронь.

<a id="payment-failure-checklist"></a>

## Отказ оплаты и повторные запросы

[Отказ оплаты](../tests/payments/test_payment_failure.py) сохраняет удержание и допускает новую попытку с другим ID. [Валидация отказа](../tests/payments/test_payment_validation.py) проверяет поле `reason` и ошибки тела.

<a id="repeated-requests-checklist"></a>

[Повторы бронирования](../tests/bookings/test_booking_idempotency.py) проверяют возврат исходного ответа с тем же ключом и телом, конфликт при изменении тела и отсутствие дублей после оплаты, отмены или истечения. Для истёкшей брони повтор возвращает исходный `201` и прежний `Location` с `Idempotency-Replayed: true`. В списке остаётся одна бронь со статусом `expired`, а `expires_at` не меняется. [Повторы платежей](../tests/payments/test_payment_repeated_requests.py) проверяют конфликты повторного создания и симуляции.

<a id="booking-payment-gaps"></a>

[Область ключа](../tests/bookings/test_booking_validation.py) проверяется между пользователями. [Матрица состояний](../tests/bookings/test_booking_payment_states.py) проверяет запреты для подтверждённых, отменённых и истёкших броней.

## Конкурентные запросы

Два потока ждут друг друга перед отправкой запросов (`Barrier`). Тест проверяет ответы и сохранённые данные для того порядка, который произошёл в этом запуске. Момент начала транзакций на сервере может различаться.

<a id="booking-concurrency"></a>

- **CON-001. Разные ключи, один номер и даты.** Один запрос создаёт бронь, второй получает `409 ROOM_NOT_AVAILABLE`. Списки владельцев и администратора подтверждают единственную бронь. [Тест](../tests/bookings/test_booking_concurrency.py)

<a id="concurrent-idempotency"></a>

- **CON-002. Одинаковый ключ и тело.** Два ответа `201` содержат одну бронь и одинаковый `Location`. Только один помечен `Idempotency-Replayed: true`. [Тест](../tests/bookings/test_booking_concurrency.py)

<a id="payment-concurrency"></a>

- **CON-003. Два создания платежа.** Один `201`, второй `409 PAYMENT_ALREADY_PENDING`. SQL подтверждает единственную запись платежа. [Тест](../tests/payments/test_payment_concurrency.py)

<a id="payment-success-concurrency"></a>

- **CON-004. Две успешные симуляции одного платежа.** Один `200`, второй `409 BOOKING_NOT_PAYABLE`. История содержит по одному переходу в `succeeded` и `confirmed`. [Тест](../tests/payments/test_payment_concurrency.py)

<a id="payment-cancellation-concurrency"></a>

- **CON-005. Оплата против отмены.** Условия, точная функция автотеста, шаги, обе допустимые ветви и ограничения описаны в [CAN-014](#cancellation-race).
