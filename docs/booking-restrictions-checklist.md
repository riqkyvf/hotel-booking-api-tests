# Ограничения создания брони

Дата: 03.11.2026. Чек-лист составлен до реализации, BR-007–010 добавлены перед расширением тестов. Последний HTTP-прогон ограничений, границ проживания, отмены и основного пути: **21 passed за 18.65 с**, включая 10 случаев этого модуля. Отчёт `junit-stay-boundaries.xml` исключён из Git. Полный набор содержит 491 случай; полный HTTP-прогон после добавления ограничений и границ не повторялся.

Основания: [FR-04](requirements.md#fr-04-бронирования), [даты и доступность](business-rules.md), [коды ошибок](api-specification.md).

| ID | Проверка | Ожидаемый результат | Статус |
|---|---|---|---|
| BR-001 | Заезд вчера по UTC, длительность допустима | 422 PAST_CHECK_IN; бронь не создаётся | Passed |
| BR-002 | Выезд в день заезда | 422 VALIDATION_ERROR, ошибка тела запроса; бронь не создаётся | Passed |
| BR-003 | Выезд раньше заезда | 422 VALIDATION_ERROR, ошибка тела запроса; бронь не создаётся | Passed |
| BR-004 | Гостей на одного больше вместимости номера, но в допустимых пределах 1–10 | availability: 200, available=false, reason=CAPACITY_EXCEEDED; POST: 409 CAPACITY_EXCEEDED; бронь не создаётся | Passed |
| BR-005 | Номер отключён администратором | availability: 200, available=false, reason=ROOM_DISABLED; POST: 409 ROOM_DISABLED; бронь не создаётся, номер остаётся отключённым | Passed |
| BR-006 | Номер архивирован администратором | availability и POST: 404 NOT_FOUND; бронь не создаётся | Passed |
| BR-007 | Заезд сегодня по UTC, обычная длительность | availability: available=true; создание 201 pending_payment; правильные даты, владелец, число ночей и сумма; GET подтверждает сохранение | Passed |
| BR-008 | Проживание 1 ночь с будущим заездом | Те же успешные результаты; сумма за одну ночь | Passed |
| BR-009 | Проживание 14 ночей с будущим заездом | Те же успешные результаты; сумма за 14 ночей | Passed |
| BR-010 | Проживание 15 ночей с будущим заездом | availability и POST: 422 VALIDATION_ERROR; ошибка POST относится к телу; бронь не создаётся | Passed |

BR-007–010 добавлены в чек-лист до реализации. Для допустимых интервалов проверяются доступность до создания, точные дата заезда/выезда, число ночей и сумма через Decimal, затем создание, GET и единственная бронь в списке владельца. Сегодня вычисляется по UTC при подготовке запроса; ожидания и подмена времени не используются.

После каждого отклонённого POST список собственного уникального пользователя содержит total=0 и items=[]. Для POST-ошибок проверяются ERROR_SCHEMA, код и совпадение request ID. Каждый случай создаёт собственный отель и номер; остальные входные данные валидны. Для BR-001 вчера определяется относительно UTC при подготовке запроса; для BR-002–006 используется будущий интервал общей фикстуры; BR-007–010 задают границы отдельно. Каждый POST получает отдельный Idempotency-Key.

Границы: это основные бизнес-ограничения, без полной матрицы типов и пропущенных полей, архивного отеля и сочетаний нескольких ошибок. Верхняя длительность проверяется на 14 и 15 ночах, без перебора всех больших значений. SQL и ожидания не используются. Ожидания не подстраиваются под дефекты приложения.

Автотесты:

- [test_booking_with_past_check_in_is_rejected](../tests/test_booking_restrictions.py#L14)
- [test_booking_with_check_out_not_after_check_in_is_rejected](../tests/test_booking_restrictions.py#L38)
- [test_booking_exceeding_room_capacity_is_rejected](../tests/test_booking_restrictions.py#L63)
- [test_booking_disabled_room_is_rejected](../tests/test_booking_restrictions.py#L93)
- [test_booking_archived_room_is_rejected](../tests/test_booking_restrictions.py#L131)
- [test_booking_with_valid_stay_boundaries_is_allowed](../tests/test_booking_restrictions.py#L161)
- [test_booking_longer_than_fourteen_nights_is_rejected](../tests/test_booking_restrictions.py#L210)
