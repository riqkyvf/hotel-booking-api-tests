# Журнал прогонов

Последний полный прогон: **519 passed за 189.45 с** (03.11.2026). JUnit XML — временные локальные артефакты; прежние отчёты удалены из корня при уборке. Имена XML и их хеши ниже сохранены для истории, наличие файлов не предполагается. Для нового прогона можно использовать `--junitxml=junit.xml`; XML исключён из Git.

- [Проверка упрощения читаемости — 03.11.2026](#readability-cleanup-run-2026-11-03)
- [Полный прогон после точечного рефакторинга](#architecture-refactor-run-2026-11-03)

<a id="smoke-run-2026-11-04"></a>

## Выделение smoke — 04.11.2026

**19 passed, 1110 deselected за 12.40 с**, 0 failures/errors/skipped. Запущены только существующие тесты, выбранные маркером smoke. Полный прогон не выполнялся. До запуска collect-only подтвердил 19 выбранных из 1129 собранных случаев.

```powershell
.\.venv\Scripts\python.exe -m pytest -m smoke -q --tb=short --junitxml=junit-smoke.xml
```

[Состав и обоснование](README.md#smoke-suite): health, регистрация/вход/профиль, каталог отелей и номеров, доступность, создание/чтение/список брони, успешная оплата, отмена в трёх состояниях платежа, запрет совпадающих дат pending_payment/confirmed, 401 без токена на трёх операциях и 403 обычному пользователю на создание отеля.

Добавлен зарегистрированный маркер smoke. Основная логика тестов, общие фикстуры, приложение и зависимости не менялись. Часть случаев отмечена через pytest.param для ограничения выборки. Прямой SQL не нужен; API использует свою БД. JUnit XML — игнорируемый локальный артефакт. Изменение карты описывает выборку, а не прирост покрытия.

<a id="health-success-run-2026-11-04"></a>

## Успешные health-проверки — 04.11.2026

**2 passed за 0.15 с**, 0 failures/errors/skipped. Запущены только два новых случая [test_health.py](../tests/test_health.py); полный набор не запускался.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_health.py -q --tb=short --junitxml=junit-health.xml
```

Публичные GET /health/live и /health/ready без авторизации: HTTP 200, Content-Type application/json и точные JSON-тела {"status":"alive"}/{"status":"ready"}. Добавлены две функции запросов в api/health.py. Подготовка пользователей/данных и прямой доступ к БД не требуются; используется работающий локальный API. Негативные ответы 503 и отключение инфраструктуры не входят в запрошенный объём. Карта обновлена: обе операции «Частично», поскольку проверяется только успешный контракт. JUnit — игнорируемый локальный артефакт.

<a id="booking-completion-run-2026-11-04"></a>

## Завершение проживания — 04.11.2026

**23 passed за 26.32 с**, 0 failures/errors/skipped: восемь новых и 15 связанных случаев состояний, идемпотентности и истечения. Python 3.14.2, локальный API/PostgreSQL. Полный прогон не выполнялся.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking_completion.py tests/test_booking_payment_states.py tests/test_booking_idempotency.py tests/test_booking_expiration.py -q --tb=short --junitxml=junit-booking-completion.xml
```

[CMP-001–003](testing-bookings.md#booking-completion): реальный completed в день выезда UTC, неизменный succeeded-платёж, запреты отмены/платёжных операций, запись в списке completed и исторический replay без новой брони. Полные SQL-истории подтверждают один системный переход confirmed→completed и отсутствие изменений платежа. Подготовка SQL меняет только даты собственной confirmed-брони с сохранением длительности и стоимости. Приложение, API-клиенты, общие фикстуры и зависимости не менялись.

Первый запуск в sandbox завершился 23 setup errors: WinError 10013 при доступе к localhost, тестовые тела не выполнялись. После предоставления процессу доступа к локальному стенду тот же целевой набор прошёл. JUnit XML — игнорируемый локальный артефакт. Точная полночь и worker в изоляции не проверялись; worker может выполнить переход до первого GET.

<a id="payment-cancellation-concurrency-run-2026-11-04"></a>

## Оплата одновременно с отменой — 04.11.2026

**24 passed за 26.39 с**, 0 failures/errors/skipped: один новый тест и 23 существующих связанных случая конкурентных платежей, отмены, повторов и состояний. Один целевой запуск; **полный прогон не выполнялся**. Python 3.14.2, локальный API и PostgreSQL; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_payment_concurrency.py tests/test_booking_cancellation.py tests/test_payment_repeated_requests.py tests/test_booking_payment_states.py -q --tb=short --junitxml=junit-payment-cancellation-race.xml
```

[CON-005](testing-bookings.md#payment-cancellation-concurrency): два потока/Barrier выполняют simulate-success и cancel. В этом запуске реализовалась cancellation_first_payment_rejected (JUnit suite property payment_cancellation_outcome): отмена 200, оплата 409 BOOKING_NOT_PAYABLE, итог cancelled/cancelled. Номер свободен; одна строка платежа, точные SQL-истории содержат создание и по одному переходу отмены без succeeded/refunded.

Тест допускает и проверяет вторую ветку 200 оплаты + 200 отмены с итогом cancelled/refunded и соответствующей историей, но этот конкретный конкурентный запуск её не подтвердил. Победитель не задаётся, повторов до нужного исхода нет; Barrier не гарантирует пересечения транзакций. Существующие API/SQL-функции, общие фикстуры, приложение и зависимости не менялись. Карта дополнена для cancel и simulate-success. JUnit XML — временный локальный артефакт, исключённый из Git.

<a id="payment-success-concurrency-run-2026-11-04"></a>

## Конкурентная успешная оплата — 04.11.2026

**11 passed за 10.08 с**, 0 failures/errors/skipped: один новый тест и десять существующих случаев конкурентного создания платежа, повторов, отказа оплаты и основного пути. Один целевой запуск; **полный прогон не выполнялся**. Python 3.14.2, локальный API и PostgreSQL; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_payment_concurrency.py tests/test_payment_repeated_requests.py tests/test_payment_failure.py tests/test_booking_flow.py -q --tb=short --junitxml=junit-payment-success-concurrency.xml
```

[CON-004](testing-bookings.md#payment-success-concurrency): два simulate-success одного платежа через Barrier/два потока дали 200 и 409 BOOKING_NOT_PAYABLE. Сохранённые состояния confirmed/succeeded и денежные поля подтверждены API. Read-only SQL подтвердил единственную строку платежа и точные истории: создание плюс по одному переходу pending→succeeded и pending_payment→confirmed, без дополнительных событий.

Добавлена get_booking_payment_history с проверкой ownership booking/user/payment, параметрами UUID и read-only-транзакцией. Существующая get_booking_payment_states переиспользована. SQL-записей нет; API-клиенты, общие фикстуры, зависимости и приложение не менялись. Карта обновлена для simulate-success; другие гонки остаются пробелами. JUnit XML — временный локальный артефакт, исключённый из Git.

<a id="payment-concurrency-run-2026-11-04"></a>

## Конкурентное создание платежа — 04.11.2026

**10 passed за 8.52 с**, 0 failures/errors/skipped: один новый конкурентный тест и девять существующих случаев повторов, отказа оплаты и основного пути. Один целевой запуск; **полный прогон не выполнялся**. Python 3.14.2, локальный тестовый API и PostgreSQL; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_payment_concurrency.py tests/test_payment_repeated_requests.py tests/test_payment_failure.py tests/test_booking_flow.py -q --tb=short --junitxml=junit-payment-concurrency.xml
```

[CON-003](testing-bookings.md#payment-concurrency): два потока/Barrier, одна свежая pending_payment-бронь, действующий JWT владельца. Получены 201 pending и 409 PAYMENT_ALREADY_PENDING; GET подтвердили платёж и неизменную бронь. Новая get_booking_payment_states читает ID/статусы всех платежей только собственной брони с проверкой user_id и read-only-транзакцией; до гонки строк ноль, после ровно одна pending с ID успешного POST. Тест отмечен db и требует БД самого API.

SQL-записи, API-функции, общие фикстуры, приложение и зависимости не менялись. Ключи JWT не извлекались. Barrier не гарантирует пересечение транзакций. Карта дополнена конкретной гонкой; другие конкурентные операции остаются пробелами. JUnit XML — временный локальный артефакт, исключённый из Git.

<a id="concurrent-idempotency-run-2026-11-04"></a>

## Конкурентная идемпотентность — 04.11.2026

**6 passed за 7.99 с**, 0 failures/errors/skipped: один новый тест одинакового ключа, один существующий конкурентный тест разных ключей и четыре последовательной идемпотентности. Один целевой запуск; **полный прогон не выполнялся**. Python 3.14.2, локальный тестовый API; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking_concurrency.py tests/test_booking_idempotency.py -q --tb=short --junitxml=junit-concurrent-idempotency.xml
```

Первоначальная попытка дала шесть ошибок подготовки: локальный API не слушал localhost:8000, Docker Engine был выключен (WinError 10061). Запущен Docker Desktop и существующие hotel-booking-db-1/api-1/worker-1, без сброса БД и пересборки приложения; после readiness повторены те же шесть тестов. Итоговый XML относится к завершённому успешному запуску.

[CON-002](testing-bookings.md#concurrent-idempotency): два потока через Barrier отправляют одинаковые тело, JWT и ключ. Проверены два 201, одинаковые JSON/ID/Location, один replay=false и один true, поздний replay с неизменным expires_at, единственная бронь в списках owner/admin и занятость номера. Порядок победителя не фиксируется. Ограничение: Barrier не доказывает пересечение серверных транзакций.

API-клиенты, приложение, зависимости и общие фикстуры не менялись; пользовательское изменение conftest сохранено. Карта обновлена для POST /bookings; уровни остались 26 «Сценарии», 1 «Частично», 2 «Нет». Конкурентные платежи и другие гонки остаются пробелами. JUnit XML — временный локальный артефакт, исключённый из Git.

<a id="booking-concurrency-run-2026-11-04"></a>

## Два конкурентных бронирования — 04.11.2026

**17 passed за 20.55 с**, 0 failures/errors/skipped: один новый конкурентный тест и 16 существующих случаев пересечений одним целевым запуском. **Полный прогон не выполнялся.** Python 3.14.2, локальный тестовый API; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking_concurrency.py tests/test_booking_overlap.py -q --junitxml=junit-booking-concurrency.xml
```

CON-001: два ThreadPoolExecutor-потока, Barrier, разные пользователи/ключи, одинаковые номер/даты. Получены 201 и 409 ROOM_NOT_AVAILABLE. Проверены снимок победителя, по одной/нулю брони в пользовательских списках, ровно одна запись у admin по своему hotel_id и занятость номера. Победитель не фиксируется заранее. Подробности и ограничение синхронизации — [CON-001](testing-bookings.md#booking-concurrency).

Barrier не доказывает пересечение транзакций на сервере; это не нагрузочный тест и не детерминированная проверка блокировок. API-функции, приложение, общие фикстуры, зависимости и конфигурация не менялись. Карта дополнена конкретной гонкой разных ключей; конкурентная идемпотентность/платежи остаются пробелами. JUnit XML — временный локальный артефакт, исключённый из Git.

<a id="booking-payment-empty-auth-run-2026-11-04"></a>

## Бронирования и платежи без токена/с пустым Bearer — 04.11.2026

**46 passed за 38.19 с**, 0 failures/errors/skipped: 14 новых случаев и 32 существующих связанных. Один целевой запуск, **полный прогон не выполнялся**. Python 3.14.2, локальный тестовый API; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking_payment_authorization.py tests/test_authorization.py tests/test_booking_access.py tests/test_admin_booking_access.py -q --junitxml=junit-booking-payment-auth.xml
```

Новый модуль проверяет только отсутствие заголовка и пустой Bearer на семи операциях: создание/чтение/отмена брони, создание/чтение/симуляции платежа. Реальный PreparedRequest подтверждает различие заголовков. Проверяются 401, ERROR_SCHEMA/request ID/WWW-Authenticate и отсутствие нежелательных изменений через API. POST выполняются с валидными данными и подходящими состояниями, после отказа владелец может создать бронь/платёж. GET списка уже имел эти проверки и не дублировался. Сценарии — [BP-AUTH-001–003](testing-auth.md#booking-payment-empty-auth).

Прочие невалидные JWT в новых тестах не добавлялись; прежние связанные тесты сохранены. Ключ JWT не использовался. API-клиенты, приложение, зависимости и общие фикстуры не менялись. В карте уточнено покрытие семи операций и оставлены прочие JWT-пробелы; уровни остались 26 «Сценарии», 1 «Частично», 2 «Нет». JUnit XML — временный локальный артефакт, исключённый из Git.

<a id="booking-payment-reading-run-2026-11-04"></a>

## Чтение брони и платежа: UUID и схемы — 04.11.2026

Новый модуль: **44 passed за 27.86 с**. Связанные проверки доступа и платёжных состояний: **30 passed за 34.53 с**. Оба запуска без failures/errors/skipped, итого 74 случая двумя целевыми запусками. **Полный прогон не выполнялся.** Python 3.14.2; локальный тестовый API и БД; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking_payment_reading.py -q --junitxml=junit-booking-payment-reading.xml
.\.venv\Scripts\python.exe -m pytest tests/test_booking_access.py tests/test_admin_booking_access.py tests/test_booking_payment_states.py -q --junitxml=junit-booking-payment-reading-related.xml
```

Добавлены BOOKING_SCHEMA/PAYMENT_SCHEMA с обязательными полями, типами, enum, UUID/date/date-time и форматами денежных строк. FormatChecker включён явно; корректность самих схем проверена Draft202012Validator.check_schema. READ-001–005 проверяют 404 для неизвестных ID, 422 с путём поля для неверных ID, схемы в шести подготовках состояний для owner/admin и семантику сумм/связей/UTC. Подробности — [READ-001–005](testing-bookings.md#booking-payment-reading).

Expired готовится существующим SQL-переносом expires_at, с меткой db. Реальный completed и матрица JWT этих ручек остаются пробелами. API-функции, приложение, зависимости и общие фикстуры не менялись. Карта: 26 операций «Сценарии», 1 «Частично», 2 «Нет». JUnit XML — временные локальные артефакты, исключённые из Git.

<a id="room-availability-run-2026-11-04"></a>

## Доступность номера — 04.11.2026

Новый модуль: **53 passed за 19.94 с**. Связанные проверки пересечений, ограничений, истечения и основного пути: **30 passed за 28.13 с**. Оба запуска без failures/errors/skipped, итого 83 случая двумя целевыми запусками. **Полный прогон не выполнялся.** Python 3.14.2, локальный тестовый API и БД; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_room_availability.py -q --junitxml=junit-room-availability.xml
.\.venv\Scripts\python.exe -m pytest tests/test_booking_overlap.py tests/test_booking_restrictions.py tests/test_booking_expiration.py tests/test_booking_flow.py -q --junitxml=junit-room-availability-related.xml
```

Сценарии [AV-001–009](testing-bookings.md#room-availability): обязательные query, форматы/границы дат и гостей, расчёт суммы/ночей, публичное чтение, ресурс/архив, приоритет причин недоступности, GET без резервирования, освобождение истёкшего удержания. Для одного случая используется существующая SQL-подготовка expires_at, без изменения статусов; остальные — API. Приложение, зависимости, API-функции и общие фикстуры не менялись. Карта: 24 операции «Сценарии», 3 «Частично», 2 «Нет». JUnit XML — временные локальные артефакты, исключённые из Git.

<a id="booking-list-run-2026-11-04"></a>

## Список бронирований — 04.11.2026

Новый модуль: **70 passed за 104.43 с**. Связанные проверки доступа user/admin: **20 passed за 21.82 с**. Оба запуска без failures/errors/skipped; итого 90 случаев двумя целевыми запусками. **Полный прогон не выполнялся.** Python 3.14.2; локальный API, незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking_list.py -q --junitxml=junit-booking-list.xml
.\.venv\Scripts\python.exe -m pytest tests/test_booking_access.py tests/test_admin_booking_access.py -q --junitxml=junit-booking-list-related.xml
```

Добавлена контролируемая выборка с четырьмя бронями владельца и одной чужой, двумя отелями и равными значениями дат/сумм. Проверены фильтры и сочетания, включительность дат, сортировки/defaults/UUID tie-break, страницы и чтение без пропусков, admin across-users внутри своего отеля, 403 user_id обычному пользователю, ошибки query/sort/range и неизвестные фильтры. Подробности — [BL-001–009](testing-bookings.md#booking-list).

Реальные expired/completed в новой выборке отсутствуют; для этих enum проверены только пустые результаты. SQL, sleep, изменения API-функций, общих фикстур, приложения и зависимостей не потребовались. Карта: 23 операции «Сценарии», 4 «Частично», 2 «Нет». JUnit XML — временные артефакты, исключённые из Git.

<a id="room-management-run-2026-11-04"></a>

## Управление номерами — 04.11.2026

Новый модуль: **86 passed за 25.50 с**. Связанные модули: **68 passed за 41.88 с**. Оба запуска без failures/errors/skipped, итого 154 случая двумя целевыми запусками. **Полный прогон не выполнялся.** Python 3.14.2, локальный тестовый API; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_room_management.py -q --junitxml=junit-room-management.xml
.\.venv\Scripts\python.exe -m pytest tests/test_room_booking_integrity.py tests/test_rooms.py tests/test_admin_operations_access.py -q --junitxml=junit-room-management-related.xml
```

Сценарии [RM-001–011](testing-hotels.md#room-management): успешный PUT, границы и валидация полей/тел, конфликт номера без частичного изменения, выключение/включение с доступностью на даты, запрет изменения архива, повтор DELETE, сохранность родителя, ID и JWT. Существующие проверки CAPACITY_IN_USE, ACTIVE_BOOKINGS_EXIST и оплаты после отключения сохранены и прошли в связанном наборе.

PUT/PATCH функций номеров получили необязательный raw_body. Приложение, зависимости, общие фикстуры и окружение не менялись. Карта: 22 операции «Сценарии», 5 «Частично», 2 «Нет»; сохранены конкретные пробелы. JUnit XML — временные локальные артефакты, исключённые из Git.

<a id="admin-users-run-2026-11-04"></a>

## Администрирование пользователей — 04.11.2026

Новый основной модуль: **50 passed за 14.89 с**. Изолированный LAST_ACTIVE_ADMIN: **3 passed за 0.56 с**. Связанные тесты: **31 passed за 13.60 с**. Все три отчёта без failures/errors/skipped. **Полный прогон не выполнялся.** Python 3.14.2; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_admin_users.py -q --junitxml=junit-admin-users.xml
.\.venv\Scripts\python.exe scripts/run_last_admin_tests.py
.\.venv\Scripts\python.exe -m pytest tests/test_admin_operations_access.py tests/test_auth_flow.py tests/test_profile.py::test_disabled_user_cannot_update_profile tests/test_login.py::test_login_with_disabled_user -q --junitxml=junit-admin-users-related.xml
```

Сценарии и границы — [AU-001–011](testing-auth.md#admin-users). Основной API: только собственные тестовые пользователи с восстановлением временно повышенной роли. LAST_ACTIVE_ADMIN: новые временные Docker PostgreSQL/API, отдельная сеть/порт, новые случайные секреты, 409 для трёх попыток изменения последнего admin. Контейнеры и сеть удалены; отдельная проверка docker ps/network ls по уникальному префиксу не нашла оставшихся ресурсов. Секреты основного стенда не извлекались.

В административном PATCH добавлен raw_body, существующие вызовы совместимы. Общие фикстуры, зависимости и приложение не изменялись. Добавлена метка isolated_admin; без отдельного API эти три теста пропускаются. JUnit: junit-admin-users.xml, junit-last-admin-isolated.xml, junit-admin-users-related.xml — временные артефакты, исключённые из Git. Карта: 19 операций «Сценарии», 8 «Частично», 2 «Нет».

<a id="hotel-management-run-2026-11-03"></a>

## Управление отелями — 03.11.2026

Новый модуль: **103 passed за 33.02 с**. Связанные модули каталога и прав: **86 passed за 31.73 с**. В обоих запусках 0 failures/errors/skipped; итого 189 случаев двумя целевыми запусками. **Полный прогон не выполнялся.** Python 3.14.2, локальный стенд; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_hotel_management.py -q --junitxml=junit-hotel-management.xml
.\.venv\Scripts\python.exe -m pytest tests/test_hotels.py tests/test_admin_operations_access.py -q --junitxml=junit-hotel-management-related.xml
```

Проверены POST/PUT с границами HotelInput, обязательность, выбранные неверные типы/null/значения, лишние поля и JSON-тела, сохранение через GET, неизменность номера при обновлении, каскадное архивирование одного номера, повтор DELETE, запрет PUT архивного отеля, запрет DELETE при pending_payment/confirmed, ошибки ID и JWT. Сценарии и ограничения — [HM-001–010](testing-hotels.md#hotel-management).

API-функции создания/обновления получили необязательный raw_body без изменения существующих вызовов. Новых зависимостей, изменений приложения и общих фикстур нет. Карта обновлена: 16 операций «Сценарии», 11 «Частично», 2 «Нет». JUnit XML — временные артефакты, исключённые из Git.

<a id="booking-payment-gaps-run-2026-11-03"></a>

## Валидация бронирований и платежей, состояния — 03.11.2026

Новые модули: **71 passed за 48.96 с**. Связанные модули: **32 passed за 30.27 с**. В обоих запусках 0 failures/errors/skipped. Итого 103 случая двумя целевыми запусками; **полный прогон не выполнялся**. Python 3.14.2, локальный тестовый стенд; незакоммиченные изменения.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking_validation.py tests/test_payment_validation.py tests/test_booking_payment_states.py -q --junitxml=junit-booking-payment-gaps.xml
.\.venv\Scripts\python.exe -m pytest tests/test_booking_idempotency.py tests/test_booking_restrictions.py tests/test_payment_failure.py tests/test_payment_repeated_requests.py tests/test_booking_expiration.py tests/test_booking_cancellation.py tests/test_booking_flow.py -q --junitxml=junit-booking-payment-related.xml
```

Проверены формат/границы/отсутствие ключа, область ключа между пользователями, поля и JSON-тела брони, валидация reason/тела отказа оплаты, запреты операций для confirmed/cancelled/expired, отказ отмены expired. Сценарии и ограничения — [BV/PV/PS](testing-bookings.md#booking-payment-gaps). Completed и отложенные JWT-claims не проверяются.

Добавлена совместимая поддержка raw_body в двух API-функциях. Существующая database_url перенесена в общий conftest, её поведение сохранено. SQL по-прежнему изменяет только expires_at собственной брони, а статусы меняет API. Приложение, зависимости и конфигурация не изменялись. Карта обновлена для пяти операций; распределение уровней осталось 13 «Сценарии», 14 «Частично», 2 «Нет». JUnit XML исключены из Git.

<a id="room-creation-reading-run-2026-11-03"></a>

## Создание и чтение номеров — 03.11.2026

Новые тесты: **87 passed за 38.99 с** (39 создания, 48 чтения). Связанные модули: **23 passed за 16.33 с**. В обоих запусках 0 failures/errors/skipped. Итого проверено 110 случаев двумя целевыми запусками; **полный прогон не выполнялся**. Python 3.14.2, локальный тестовый API; рабочая копия с незакоммиченными изменениями.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_room_creation.py tests/test_rooms.py -q --junitxml=junit-room-creation-reading.xml
.\.venv\Scripts\python.exe -m pytest tests/test_booking_flow.py tests/test_room_booking_integrity.py tests/test_admin_operations_access.py -q --junitxml=junit-room-reading-related.xml
```

Добавлены два тестовых модуля и ROOM_SCHEMA с проверкой форматов UUID/timestamps. Функции list_rooms/get_room получили необязательный access_token для проверки admin-доступа к архиву; обратная совместимость подтверждена связанными тестами. Сценарии и ограничения — [RC-001–005, RR-READ-001–007](testing-hotels.md#room-creation-reading).

Карта обновлена: создание, список и детали номеров имеют уровень «Сценарии». Всего 13 операций «Сценарии», 14 «Частично», 2 «Нет». Уровень не означает исчерпывающего покрытия. Приложение, общие фикстуры, зависимости и настройки окружения не изменялись; ключ JWT не использовался. JUnit XML — временные артефакты, исключённые из Git.

<a id="admin-operations-access-run-2026-11-03"></a>

## Права на административные операции — 03.11.2026

**32 passed за 17.13 с**, 0 failures, 0 errors, 0 skipped. Только новые и связанные модули: 14 случаев прав административных операций, 12 общей авторизации и 6 целостности бронирований. Python 3.14.2; локальный API; незакоммиченные изменения. **Полный прогон не выполнялся**; результат 519 passed выше относится к предыдущему состоянию проекта.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_admin_operations_access.py tests/test_authorization.py tests/test_room_booking_integrity.py -q --junitxml=junit-admin-operations-access.xml
```

Добавлены API-функции PUT отеля и GET списка/деталей пользователей admin. Они возвращают Response без проверки статуса. Общие фикстуры, приложение и зависимости не изменены. Сценарии [ADM-001–010](testing-auth.md#admin-operations-access) проверяют 403 обычному user на 10 операциях, сохранность ресурсов и отсутствие самоповышения роли/деактивации. Карта обновлена: 10 операций «Сценарии», 17 «Частично», 2 «Нет». JUnit — временный артефакт, исключённый из Git.

<a id="room-integrity-run-2026-11-03"></a>

## Изменение номеров и целостность бронирований — 03.11.2026

**519 passed за 189.45 с**, 0 failures, 0 errors, 0 skipped. Все 19 модулей, включая SQL-сценарий истечения брони. Python 3.14.2, локальный тестовый стенд; рабочая копия с незакоммиченными изменениями. Отдельный прогон нового модуля: **6 passed за 6.71 с**.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_room_booking_integrity.py -q --junitxml=junit-room-booking-integrity.xml
.\.venv\Scripts\python.exe -m pytest -q --junitxml=junit-room-integrity-full.xml
```

Добавлены `api.rooms.update_room` (PUT, возвращает Response без проверки статуса) и четыре сценария в [test_room_booking_integrity.py](../tests/test_room_booking_integrity.py): запреты уменьшения вместимости и архивирования при pending_payment/confirmed, сохранение снимка цены при изменении номера, оплата существующей брони после отключения номера. Первые два сценария параметризованы двумя состояниями, всего шесть случаев. Подробные ожидания — [RBI-001–004](testing-bookings.md#room-booking-integrity).

Карта покрытия обновлена: PUT номера, DELETE номера и PATCH доступности имеют уровень «Частично»; валидация, роли и остальные пробелы сохранены. Итог: 10 операций «Сценарии», 10 «Частично», 4 «Подготовка», 5 «Нет». Проверены 29 уникальных операций и локальные ссылки документации; `git diff --check` пройден. Приложение, зависимости и общие фикстуры не изменялись. Ключ JWT не использовался, отложенные проверки exp/iss/aud не добавлялись.

JUnit XML — временные локальные отчёты, исключённые из Git. Ниже сохранены результаты предыдущих состояний проекта.

<a id="authorization-run-2026-11-03"></a>

## Общая авторизация — 03.11.2026

**513 passed за 184.13 с**, 0 failures, 0 errors, 0 skipped. Все 18 модулей, включая SQL-сценарий истечения брони. Python 3.14.2; локальный API и тестовая БД; рабочая копия с незакоммиченными изменениями. Отдельный прогон нового блока до окончательного удаления отложенных тестов: 12 passed за 3.13 с, 3 deselected (проверки с ключом подписи не выполнялись). В итоговом наборе этих трёх тестов нет.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=junit-authorization-full.xml
```

Добавлено 12 случаев в [test_authorization.py](../tests/test_authorization.py): отсутствие заголовка, пустой Bearer, некорректный JWT, повреждённая подпись; каждый вариант проверяется на GET профиля, GET списка бронирований и POST отеля с валидным телом. Проверяются 401 UNAUTHORIZED, схема ошибки, request ID, WWW-Authenticate, отсутствие токена в ошибке и сохранение доступа с действующим токеном.

Корректно подписанные JWT с истёкшим exp или неверными iss/aud отложены по решению владельца. Ключ стенда не извлекался и не сохранялся. Модификация подписи не считается проверкой этих claims. Зависимости и настройки окружения не изменены.

JUnit полного прогона: `junit-authorization-full.xml`, временный локальный артефакт, исключён из Git. Исторические результаты ниже относятся к предыдущим состояниям исходников.

<a id="readability-cleanup-run-2026-11-03"></a>

## Проверка упрощения читаемости — 03.11.2026

Полный прогон: **501 passed за 179.99 с**, 0 failures, 0 errors, 0 skipped. Проверены все 17 модулей, включая SQL-сценарий истечения брони. Python 3.14.2, локальный API и тестовая БД.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=junit-readability-cleanup.xml
```

JUnit на момент прогона: `junit-readability-cleanup.xml` (удалён при уборке, исключён из Git). Прогон выполнен с незакоммиченными изменениями.

<a id="readability-cleanup-run-2026-11-03-изменения"></a>

### Изменения

1. `private_booking` переименована в `booking_with_payment`; описание фиксирует состав результата и два параметризованных состояния. Цепочка подготовки сохранена.
2. `booking_to_cancel` перечитывает платёж после подготовки и проверяет его статус и неизменяемые поля. Возвращаемые бронь и платёж теперь описывают текущее состояние; без платежа возвращается None.
3. `disabled_user` переименована в `disabled_user_credentials`; у `second_user` ключ `token` заменён на `access_token`. Обновлены все потребители; составные результаты фикстур описаны в docstring.
4. В сценариях отмены уточнены имена ответов и снимков, добавлены короткие комментарии этапов. Проверки и последовательность бизнес-действий сохранены.
5. `create_priced_hotel` проверяет состояния всех номеров до первого HTTP-запроса: допустимы active, disabled, archived. Словари и пары данных сохранены.
6. Удалены 30 неиспользуемых присваиваний результата `assert_api_error`; вызовы и проверки остаются.

Дополнительно: сборка 501 случая; `git diff --check`; проверка с подменённым API-вызовом показала, что ошибочное состояние `disbaled` отклоняется до создания отеля. Предыдущая запись в этом журнале о точечном рефакторинге относится к состоянию исходников до этого упрощения.

SHA-256 JUnit: `7507c9820b5af46adee9e25cce5a7fa2dba3264a7c4afea5c3683400490ead8d`.

<a id="architecture-refactor-run-2026-11-03"></a>

## Полный прогон после точечного рефакторинга

Дата: 03.11.2026 (Asia/Irkutsk).

<a id="architecture-refactor-run-2026-11-03-результат"></a>

### Результат

**501 passed за 179.94 с**, 0 failures, 0 errors, 0 skipped. Выполнены все 17 модулей, включая тест с меткой `db`. Результат подтверждён JUnit XML, а не только сборкой тестов.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=junit-architecture-refactor.xml
```

JUnit на момент прогона: `junit-architecture-refactor.xml` (удалён при уборке, исключён из Git). SHA-256 отчёта: `fdb565b4db6b3be7aa00aa94ac3d1a8fc43e9637ab403c3a1dddff20d81d8b6d`.

Начальная попытка в ограниченной среде прервана из-за запрета сетевого доступа Windows (`WinError 10013`). Итог выше относится к завершённому повторному запуску с доступом к локальному стенду.

<a id="architecture-refactor-run-2026-11-03-проверенные-изменения"></a>

### Проверенные изменения

- `api/headers.py`: единая функция `authorization_headers`. `None` не отправляет Authorization, пустая строка отправляет пустой Bearer; остальные значения передаются без нормализации.
- Все 18 API-функций с авторизацией используют эту функцию. Idempotency-Key и Content-Type сохраняются.
- `tests/assertions.py`: общий контракт ошибки (статус, JSON Schema, код, наличие и совпадение request ID).
- 38 повторяющихся блоков в 13 модулях заменены `assert_api_error`. Конкретные поля, WWW-Authenticate, проверки секретов и последствий операции остались в сценариях.
- `tests/__init__.py`: явный пакет для импорта помощника.

Дополнительно выполнены локальные проверки без обращения к стенду: три режима токена; отсутствие Authorization во всех 18 функциях; принятие корректного ответа помощником и отклонение неверных статуса, кода, схемы и request ID. Статическая сверка подтвердила сохранение количества assert с учётом вынесенных четырёх проверок на каждый вызов помощника. `git diff --check` пройден.

<a id="architecture-refactor-run-2026-11-03-версии-и-границы-воспроизводимости"></a>

### Версии и границы воспроизводимости

- Python: **3.14.2**.
- Базовый commit тестов: `a3e4e70484142ce6a2b18c85a7ce1b2570aaf4c9`. Прогон выполнен с незакоммиченными изменениями, описанными выше; это не результат чистого commit.
- Отпечаток проверенных исходников и конфигурации: `81e2ab2ee63a79b4f69df0d5c917dee82a1d3b03ef832f22397f6a82571d034b`. Алгоритм: SHA-256 UTF-8-манифеста ниже; пути отсортированы, каждая строка имеет вид `sha256  path` и заканчивается LF. `.env` и секреты в отпечаток не входят.
- API: локальный стенд `http://localhost:8000/api/v1`, контейнер `hotel-booking-api-1`, образ `hotel-booking-api`.
- ID запущенного образа API: `sha256:07089aeb01e4eba54350c711176bacf8a125627dbe40a9a86cb1c93af70ec50b`.
- Время создания образа: `2026-11-03T05:52:16.290112981Z`; подключённых томов у контейнера API нет.
- Контейнеры стенда: `hotel-booking-api-1`, `hotel-booking-worker-1`, `hotel-booking-db-1`; БД использует образ `postgres:17-alpine`.
- HEAD локального репозитория приложения: `a515cdb5deffac1106839aa78d3e3bb1171dbe51`; есть изменения в `app/schemas/__init__.py`, `docs/api-specification.md`, `docs/database-schema.md`, `docs/requirements.md`. Соответствие этого HEAD исходникам запущенного образа не подтверждено; для идентификации исполняемого API используется ID образа выше.
- БД перед прогоном не сбрасывалась; созданные тестами данные остаются согласно существующей стратегии проекта. Результат не подтверждает параллельный запуск и не является проверкой другого образа приложения.

<a id="architecture-refactor-run-2026-11-03-манифест-проверенных-файлов"></a>

### Манифест проверенных файлов

```text
bfdc81c1e2190c03a69ff08a33f564318d2153a591ca5f75201d908f8e6f7c81  api/auth.py
2e627fafeddd4f2c6df0f45300f04755bd24f7e934ef0492dc956078f2986ed5  api/bookings.py
ec57589ae8e2ff3ec84ed9cfff37f897668da0fdbe1667bfc2151d7b2e814856  api/headers.py
e4ad360d261c992d93b96e7ed5ac23e3999e83ef883362dcf51ea4bc11b1e940  api/hotels.py
c9fa32abc8a44caa99f7654b8cb0c65a40aa6f7794ca6b9beec43fcf23de5086  api/payments.py
8001ca5c4d11bef777e72e919b6507f08cb3ba8d142dd6ed212d66f351c45f06  api/rooms.py
4baef5cddbb4541a1789733c130db2d5798c8974175474bcdd1db705208fd9e7  api/users.py
0fe73ae498574d2746d2e6bbe8c55d865c86875e711f758a3e07ab896484e917  data/__init__.py
85d03359a5ad55831b240ea45fdadc893ecc2ad6b9ded417a7b09a4e5c0822b9  data/auth.py
7652deeeceb0c013eae6b8b2a12ab2b3e9df25300242d3dd6ee09efc59c0c471  data/booking.py
f76a6ccedc2f075e43b9addfd7488723e7bef896caa1e43633a62e33ff575079  data/hotel_prices.py
78219941ec4e3cc31c7e4ba681a0ee870d99776c59822d9c04ddc837165ed950  data/hotels.py
e888b054d34d2eb99b27ec668576a28a091e18c576e9fbb496cac0a80b28bf56  data/payments.py
12988d0562e14e0d3b696ed935ae8488323c9bebcea75e61393f48230a38a28a  data/profile.py
089f70dac134658eb34ceacb03ab9bcd5cdb0068676cc0b18a6f6126fe602d65  db.py
f84a6d6f83368bd61e13718c4747d8dc23681730fa21f9fc07cad40b8c22256c  pytest.ini
f268dc94e2747dd7865f1bbdd7f5309ce538f2089340367ce84bff2f96f0f853  requirements.txt
d50a0b365b10e5e39fa9ddce210cf2bf56ac57a17bb7cc81ecf61feb52a28464  schemas/error_response.py
563a57d4bc2389493ad28363705f42188715eeede70e4f2f3650a513e701dda8  schemas/hotel_response.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  tests/__init__.py
5408d401c0e43ec5f3f9826bc978096581171255e9e8fd5714cb07be9b40c5d5  tests/assertions.py
30777286ce8808cc66347d8fb177fffa45ae8092e68a92162a5f5f4c75b955ce  tests/conftest.py
37ed1e54b34caa803e4dd3b0f6036dcb78a9a05d04f0ebeffa10f8551c8b071c  tests/test_admin_booking_access.py
4fd6c9be77e916bcefab30d97487fe2887ab1b6ada1b9f1bed961257984a4809  tests/test_auth_flow.py
3dc17c73514de9204ec2d830e295dc4731a7d13e51eb10384d44af948b8ad1f3  tests/test_booking_access.py
8f1d44a72bd5c6dfe0b5422c01bcdcb0459fbe0cb874b0ca0507d32c40d96c20  tests/test_booking_cancellation.py
06d80fd67a63fafe9a1b1ace2caf71334561c5e568afa463ad470f4d2444e0a0  tests/test_booking_expiration.py
8636dac26fd72124b124df75949c92f3a94c4a248bdbc7ea37215591f8a232a6  tests/test_booking_flow.py
cbfc55a12e01e6b10ce927461d106fefb0c7e3c9b280be9ac1a87d2365edfeaf  tests/test_booking_idempotency.py
7b8b67cad29e16e3b1cf1d79f989b1ae06337b2a67fe4b0e44b0232b83572a03  tests/test_booking_overlap.py
ec4f65780edf2d7d1ceeeace0476e07f98ba0495b580ee64e69b1d465ffda634  tests/test_booking_restrictions.py
4d3355d894b1d35479793d32941d142416903c93423a8199ec063cc93dd74f43  tests/test_hotel_prices.py
ed657e4870d63259aa6ee93374ae07457c1ec1b5addeb2396eee78630721ff36  tests/test_hotels.py
48e43074295136d347c07c6ff6db4e8ae0c4e30850c5e13e71a2975cadcf553a  tests/test_login.py
1c6455d423571058a200ae4f85c6567e731419f2d6292f7856ad3174af84b8e2  tests/test_payment_failure.py
0bcf7779c8398e87b2c48de46f1a60c948171e8bad606514cfe1bf94e3c66ae4  tests/test_payment_repeated_requests.py
bbd0f8aaa9ff77618296a9c964bef03ef772d8319488e199095a02f2ef93a686  tests/test_profile.py
ed38b77797aa3c161d50cc48a0a70776176b05532bf350e113b230ab7427504c  tests/test_registration.py
```

## Исторические результаты отдельных этапов

Эти записи описывают состояние на момент соответствующего этапа, до последующих полных прогонов. Указания «полный прогон не выполнялся» относятся только к тому моменту.

### Чек-лист регистрации пользователя

> Последний полный HTTP-прогон от 03.11.2026: **431 passed за 114.06 с**, включая 105 случаев изменения профиля и 102 случая чтения каталога отелей (72 общих и 30 ценовых). Перенос данных и raw_body проверены этим прогоном. Локальный отчёт — `junit.xml`; commit запущенного приложения не зафиксирован.

### Чек-лист регистрации пользователя

**Операция:** `POST /api/v1/auth/register`  
**Окружение:** локальное API, `http://localhost:8000`  
**Дата составления:** 01.11.2026  
**Версия приложения / commit:** не зафиксирована  
**Дата ручного прогона:** не зафиксирована  
**Последний полный автопрогон:** 03.11.2026 — 431 passed за 114.06 с; HTTP-прогон обновлённого набора, отчёт `junit.xml`.

### Чек-лист регистрации пользователя

Статусы обновлены по полному HTTP-прогону 03.11.2026: 431 passed. Отчёт `junit.xml` создан локально и исключён из Git. Колонка «Автотест / покрытие» связывает пункт с тестом и указывает ограничения. Колонка подтверждений не используется.

### Чек-лист регистрации пользователя


- `Passed` — пункт покрыт прошедшими автотестами.
- `Partial` — прошла только часть проверки; оставшаяся часть указана в колонке покрытия.
- `Not run` — соответствующего автотеста нет; в этом прогоне пункт не выполнялся.
- `Требует уточнения` — ожидаемое поведение ещё не согласовано.
- `Failed` / `Blocked` — расхождение с ожиданием / препятствие выполнению; в текущем прогоне таких результатов нет.

### Чек-лист регистрации пользователя

Всего пунктов: 103; 83 Passed, 13 Partial, 7 Not run. Это покрытие пунктов, а не процент готовности продукта.

### Чек-лист регистрации пользователя

Один пункт чек-листа может соответствовать нескольким запускам параметризованного теста, а один тест — нескольким пунктам. Поэтому 431 passed по проекту не означает 431 полностью закрытых пунктов этого чек-листа.

### Чек-лист входа пользователя

> Последний полный HTTP-прогон от 03.11.2026: **431 passed за 114.06 с**, включая 105 случаев изменения профиля и 102 случая чтения каталога отелей (72 общих и 30 ценовых). Перенос данных и raw_body проверены этим прогоном. Локальный отчёт — `junit.xml`; commit запущенного приложения не зафиксирован.

### Чек-лист входа пользователя

**Операция:** `POST /api/v1/auth/login`  
**Окружение:** локальное API, `http://localhost:8000`  
**Дата составления:** 01.11.2026  
**Последний полный автопрогон:** 03.11.2026 — 431 passed за 114.06 с; HTTP-прогон обновлённого набора, отчёт `junit.xml`.

### Чек-лист входа пользователя

`Passed` — проверка выполнена прошедшим автотестом; `Not run` — пока не автоматизирована и не выполнялась в последнем прогоне; `Требует уточнения` — ожидаемое поведение нужно согласовать. `Failed` и `Blocked` в последнем прогоне отсутствуют.

### Чек-лист входа пользователя


Всего пунктов: 41; 40 Passed, 1 Not run. Это покрытие пунктов, а не процент готовности продукта.

### Чек-лист входа пользователя

Существующие автотесты не доказывают полное покрытие login и авторизации. Сценарии в этом документе связаны с фактическими проверками кода; невыполненные проверки не отмечены Passed.

### Чек-лист изменения профиля

HTTP-прогон модуля от 03.11.2026: **105 passed за 33.37 с**. Локальный отчёт — `junit-profile.xml` (исключён из Git). Полный регрессионный прогон — **431 passed за 114.06 с**, отчёт `junit.xml`. Всего 17 пунктов чек-листа, каждый подтверждён прошедшими тестами; число пунктов не равно числу параметризованных случаев.

### Решения и открытые вопросы к требованиям регистрации

Решения по email и паролю согласованы владельцем учебного проекта 03.11.2026. Нормативное описание — [FR-01](requirements.md#fr-01-пользователи-и-авторизация). Ограничения реализованы в локальном коде приложения; полный набор HTTP-тестов, включая регистрацию, вход, профиль и чтение отелей, прошёл 03.11.2026 (431 passed); ранее наблюдавшийся приём кириллицы и пробелов описывает прежнее поведение.

### Чек-лист чтения каталога отелей

Чек-лист создан до реализации тестов. После упрощения 03.11.2026 выполнен HTTP-прогон каталога, цен и основного пути бронирования: **107 passed за 57.50 с**, из них 72 общих и 32 ценовых случая каталога. Отчёт — `junit-readability.xml` (исключён из Git). Все 43 пункта HL/HD/HP подтверждены; число пунктов не равно числу параметризованных случаев. Последний полный прогон до добавления бронирования и этого упрощения: **431 passed за 114.06 с**, отчёт `junit.xml`. Commit запущенного приложения не зафиксирован.

### Основной путь: выбор номера, бронирование и успешная оплата

Дата: 03.11.2026. Приоритет: основной пользовательский путь. Чек-лист создан до реализации. HTTP-прогон нового модуля: **3 passed за 2.01 с**, отчёт `junit-booking-flow.xml` (исключён из Git). После упрощения каталога эти три сценария повторно прошли в составе запуска **107 passed за 57.50 с**, отчёт `junit-readability.xml`. После добавления пересечений модуль снова проверен: **19 passed за 19.02 с** вместе с 16 новыми случаями, отчёт `junit-booking-overlap.xml`. После добавления отмены три модуля бронирования проверены вместе: **22 passed за 23.49 с**, отчёт `junit-booking-cancellation.xml`. На этапе добавления отмены набор содержал 455 случаев; полный регрессионный прогон после этих изменений не повторялся. Commit запущенного приложения не зафиксирован.

### Ограничения создания брони

Дата: 03.11.2026. Чек-лист составлен до реализации, BR-007–010 добавлены перед расширением тестов. Последний HTTP-прогон ограничений, границ проживания, отмены и основного пути: **21 passed за 18.65 с**, включая 10 случаев этого модуля. Отчёт `junit-stay-boundaries.xml` исключён из Git. Полный набор содержит 491 случай; полный HTTP-прогон после добавления ограничений и границ не повторялся.

### Пересечение дат бронирования

Дата: 03.11.2026. Чек-лист составлен до реализации. HTTP-прогон: **19 passed за 19.02 с** — 16 случаев пересечений и 3 прежних сценария основного пути. Отчёт `junit-booking-overlap.xml` исключён из Git. После добавления отмены три модуля бронирования проверены вместе: **22 passed за 23.49 с**, отчёт `junit-booking-cancellation.xml`. На этапе добавления отмены набор содержал 455 случаев; после добавления этих 16 случаев полный HTTP-прогон не повторялся.

### Пересечение дат бронирования

После упрощения фикстур: **68 passed за 65.34 с** по всем модулям бронирования и платежей, отчёт `junit-fixture-refactor.xml`. Подготовка пересечений использует собственные OVERLAP_NIGHTS и OVERLAP_CHECK_IN_OFFSET_DAYS через локальную overlap_stay; от обычной stay_dates и её длительности она не зависит.

### Отмена брони и освобождение номера

Дата: 03.11.2026. Чек-лист составлен до реализации, BC-004–008 добавлены перед расширением тестов. Последний HTTP-прогон отмены, идемпотентности бронирования и основного пути: **15 passed за 16.62 с**, включая 8 случаев отмены. Отчёт `junit-cancellation-boundaries.xml` исключён из Git. На этапе добавления границ отмены набор содержал 487 случаев; полный HTTP-прогон после добавления ограничений бронирования и границ отмены не повторялся.

### Истечение удержания: подготовка через SQL

Дата: 03.11.2026. Чек-лист составлен до реализации. Новый SQL-тест вместе с отказом оплаты, повторными платёжными запросами и основным путём: **10 passed за 9.42 с**. Отчёт `junit-booking-expiration.xml` исключён из Git. Набор содержит 501 случай; полного повторного прогона после добавления SQL-теста не было.

### Доступ к чужим бронированиям и платежам

Дата: 03.11.2026. Чек-лист составлен до реализации; BA-004/005/006 добавлены перед расширением тестов. Последний полный HTTP-прогон: **476 passed за 169.98 с**, включая 11 случаев доступа. Отчёт `junit-full-payment-access.xml` исключён из Git. Все шесть пунктов подтверждены прогоном.

### Права администратора на чужие брони и платежи

Дата: 03.11.2026. Чек-лист составлен до реализации. HTTP-прогон всех девяти модулей бронирования и платежей: **67 passed за 69.69 с**, включая 9 новых случаев admin. Отчёт `junit-admin-booking-access.xml` исключён из Git. Полный набор содержит 500 случаев; после добавления этих сценариев полный HTTP-прогон не повторялся.

### Неуспешная оплата

Дата: 03.11.2026. Чек-лист составлен до реализации. HTTP-прогон пяти модулей бронирования и платежей: **31 passed за 33.32 с**, включая 3 новых случая. Отчёт `junit-payment-failure.xml` исключён из Git. На этапе добавления отказа оплаты набор содержал 464 случая; после добавления неуспешной оплаты полный HTTP-прогон не повторялся.

### Повторные запросы бронирования и оплаты

Дата: 03.11.2026. Чек-лист составлен до реализации. HTTP-прогон семи модулей бронирования и платежей: **38 passed за 40.36 с**, включая 7 новых случаев. Отчёт `junit-repeated-requests.xml` исключён из Git. Полный набор содержит 471 случай; после добавления повторных запросов полный HTTP-прогон не повторялся.

