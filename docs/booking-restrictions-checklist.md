# Ограничения создания брони

Дата: 03.11.2026. Чек-лист составлен до реализации. HTTP-прогон ограничений, основного пути и пересечений: **25 passed за 24.63 с**, включая 6 новых случаев. Отчёт `junit-booking-restrictions.xml` исключён из Git. На этапе добавления ограничений набор содержал 482 случая; после добавления ограничений полный HTTP-прогон не повторялся.

Основания: [FR-04](requirements.md#fr-04-бронирования), [даты и доступность](business-rules.md), [коды ошибок](api-specification.md).

| ID | Проверка | Ожидаемый результат | Статус |
|---|---|---|---|
| BR-001 | Заезд вчера по UTC, длительность допустима | 422 PAST_CHECK_IN; бронь не создаётся | Passed |
| BR-002 | Выезд в день заезда | 422 VALIDATION_ERROR, ошибка тела запроса; бронь не создаётся | Passed |
| BR-003 | Выезд раньше заезда | 422 VALIDATION_ERROR, ошибка тела запроса; бронь не создаётся | Passed |
| BR-004 | Гостей на одного больше вместимости номера, но в допустимых пределах 1–10 | availability: 200, available=false, reason=CAPACITY_EXCEEDED; POST: 409 CAPACITY_EXCEEDED; бронь не создаётся | Passed |
| BR-005 | Номер отключён администратором | availability: 200, available=false, reason=ROOM_DISABLED; POST: 409 ROOM_DISABLED; бронь не создаётся, номер остаётся отключённым | Passed |
| BR-006 | Номер архивирован администратором | availability и POST: 404 NOT_FOUND; бронь не создаётся | Passed |

После каждого отклонённого POST список собственного уникального пользователя содержит total=0 и items=[]. Для POST-ошибок проверяются ERROR_SCHEMA, код и совпадение request ID. Каждый случай создаёт собственный отель и номер; остальные входные данные валидны. Для BR-001 вчера определяется относительно UTC при подготовке запроса; для остальных дат используется будущий интервал общей фикстуры. Каждый POST получает отдельный Idempotency-Key.

Границы: это основные бизнес-ограничения, без полной матрицы типов и пропущенных полей, длительности свыше 14 ночей, архивного отеля и сочетаний нескольких ошибок. SQL и ожидания не используются. Ожидания не подстраиваются под дефекты приложения.

Автотесты:

- [test_booking_with_past_check_in_is_rejected](../tests/test_booking_restrictions.py#L13)
- [test_booking_with_check_out_not_after_check_in_is_rejected](../tests/test_booking_restrictions.py#L37)
- [test_booking_exceeding_room_capacity_is_rejected](../tests/test_booking_restrictions.py#L62)
- [test_booking_disabled_room_is_rejected](../tests/test_booking_restrictions.py#L92)
- [test_booking_archived_room_is_rejected](../tests/test_booking_restrictions.py#L130)
