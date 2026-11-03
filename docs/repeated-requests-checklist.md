# Повторные запросы бронирования и оплаты

Дата: 03.11.2026. Чек-лист составлен до реализации. HTTP-прогон семи модулей бронирования и платежей: **38 passed за 40.36 с**, включая 7 новых случаев. Отчёт `junit-repeated-requests.xml` исключён из Git. Полный набор содержит 471 случай; после добавления повторных запросов полный HTTP-прогон не повторялся.

Основания: [FR-06](requirements.md#fr-06-идемпотентность), [FR-07](requirements.md#fr-07-тестовые-платежи), [контракт API](api-specification.md).

Idempotency-Key применяется только к POST /bookings. Создание платежа не идемпотентно: повтор при существующем pending даёт конфликт, а новая попытка после failed создаёт другой ID. Этот разрешённый повтор после отказа покрыт [отдельно](payment-failure-checklist.md).

| ID | Проверка | Ожидаемый результат | Статус |
|---|---|---|---|
| RR-001 | Дважды создать бронь с одним ключом и тем же телом, изменив только порядок JSON-полей | Оба ответа 201, одинаковый исходный JSON; Idempotency-Replayed false/true; одинаковый Location на бронь; GET и список подтверждают единственную бронь | Passed |
| RR-002 | Тот же ключ с другим валидным числом гостей | 409 IDEMPOTENCY_KEY_REUSED; исходная бронь не изменена, в списке одна запись | Passed |
| RR-003 | Повторить исходный запрос после отмены | 201 с исходным pending_payment-снимком; GET остаётся cancelled; список содержит только исходный ID, номер доступен | Passed |
| RR-004 | Повторить исходный запрос после успешной оплаты | 201 с исходным pending_payment-снимком; GET остаётся confirmed; succeeded-платёж не изменён; в списке одна бронь | Passed |
| RR-005 | Повторно создать платёж для брони с pending-платежом | 409 PAYMENT_ALREADY_PENDING; исходный pending-платёж и бронь сохраняются | Passed |
| RR-006 | Повторить симуляцию успеха succeeded-платежа | 409 BOOKING_NOT_PAYABLE; succeeded и confirmed сохраняются без изменений | Passed |
| RR-007 | Повторить симуляцию отказа failed-платежа с другой причиной | 409 PAYMENT_STATE_CONFLICT; исходная причина и failed сохраняются, бронь остаётся pending_payment | Passed |

Для 409 проверяются ERROR_SCHEMA и совпадение request ID. Срок бронирования не должен продлеваться: сравнение сохранённой брони включает expires_at. Каждый сценарий создаёт собственные ресурсы. HTTP API не предоставляет список платежей: для RR-005 проверяются контрактный отказ и сохранность известной операции, без заявления о проверке числа строк БД.

Границы: последовательные запросы. Параллельность, матрица формата ключей, истечение, область ключа между пользователями и повтор после completed остаются отдельными этапами. SQL, ожидания и исправления приложения ради зелёного прогона не используются.

Автотесты:

- [test_same_key_and_body_replay_original_booking](../tests/test_booking_idempotency.py#L30)
- [test_same_key_with_different_body_is_rejected](../tests/test_booking_idempotency.py#L50)
- [test_replay_after_cancellation_does_not_create_new_booking](../tests/test_booking_idempotency.py#L72)
- [test_replay_after_payment_preserves_confirmed_booking](../tests/test_booking_idempotency.py#L107)
- [test_second_pending_payment_is_rejected](../tests/test_payment_repeated_requests.py#L14)
- [test_repeated_payment_success_is_rejected](../tests/test_payment_repeated_requests.py#L34)
- [test_repeated_payment_failure_preserves_original_reason](../tests/test_payment_repeated_requests.py#L63)
