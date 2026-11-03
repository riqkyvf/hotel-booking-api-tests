# Чек-лист входа пользователя

> Последний полный HTTP-прогон от 03.11.2026: **431 passed за 114.06 с**, включая 105 случаев изменения профиля и 102 случая чтения каталога отелей (72 общих и 30 ценовых). Перенос данных и raw_body проверены этим прогоном. Локальный отчёт — `junit.xml`; commit запущенного приложения не зафиксирован.

**Операция:** `POST /api/v1/auth/login`  
**Окружение:** локальное API, `http://localhost:8000`  
**Дата составления:** 01.11.2026  
**Последний полный автопрогон:** 03.11.2026 — 431 passed за 114.06 с; HTTP-прогон обновлённого набора, отчёт `junit.xml`.

**Версия приложения / commit:** не зафиксирована.

Основание: [FR-01 и FR-02](requirements.md), [контракт API](api-specification.md) и схема Login из OpenAPI. Login принимает только email и password. Для пароля схема задаёт длину 10–128 символов; для email — корректный формат и максимум 254 символа.

`Passed` — проверка выполнена прошедшим автотестом; `Not run` — пока не автоматизирована и не выполнялась в последнем прогоне; `Требует уточнения` — ожидаемое поведение нужно согласовать. `Failed` и `Blocked` в последнем прогоне отсутствуют.

Примеры данных в таблицах обозначают варианты проверки. В коде используются уникальные email. Каждый вариант параметризации запускается отдельно; количество строк чек-листа не равно количеству запусков тестов.


Всего пунктов: 41; 40 Passed, 1 Not run. Это покрытие пунктов, а не процент готовности продукта.

## 1. Основные сценарии

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-001 | Успешный вход | Активный зарегистрированный пользователь; верные email и пароль | `200`; access_token — непустая строка, token_type = bearer, expires_in = 3600 | Passed | [test_login_with_valid_credentials](../tests/test_login.py#L9) |
| LOGIN-002 | Неверный пароль | Существующий email; другой пароль допустимой длины | `401`, error.code = INVALID_CREDENTIALS | Passed | [test_login_with_invalid_password](../tests/test_login.py#L39) |
| LOGIN-003 | Несуществующий email | Уникальный валидный email без регистрации | `401`, error.code = INVALID_CREDENTIALS | Passed | [test_login_with_nonexistent_email](../tests/test_login.py#L65) |
| LOGIN-004 | Вход отключённого пользователя | Создать пользователя и отключить через admin API; передать правильный пароль | `401`, error.code = INVALID_CREDENTIALS; access_token отсутствует | Passed | [test_login_with_disabled_user](../tests/test_login.py#L48) |

Пользователя для LOGIN-004 создаёт фикстура disabled_user. Для подготовки доступа администратора используется локальная seed-учётная запись из [документации](README.md); готовый disabled@example.com не используется.

## 2. Email и пароль

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-005 | Верхний регистр email | Изменить регистр email существующего пользователя | `200`; непустой access_token | Passed | [test_login_normalizes_email](../tests/test_login.py#L23) [uppercase] |
| LOGIN-006 | Крайние пробелы email | Окружить существующий email пробелами | `200`; непустой access_token | Passed | [test_login_normalizes_email](../tests/test_login.py#L23) [spaces] |
| LOGIN-007 | Регистр и пробелы вместе | Верхний регистр email и пробелы по краям | `200`; непустой access_token | Passed | [test_login_normalizes_email](../tests/test_login.py#L23) [both] |
| LOGIN-008 | Email не передан | Удалить email из тела | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_without_required_field](../tests/test_login.py#L73) [email] |
| LOGIN-009 | Пароль не передан | Удалить password из тела | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_without_required_field](../tests/test_login.py#L73) [password] |
| LOGIN-010 | Null в обязательных полях | По отдельности email = null и password = null | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_null_required_field](../tests/test_login.py#L89) |
| LOGIN-011 | Неверные типы полей | Для каждого поля отдельно: целое число, дробное число, true, false, массив, объект | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_field_type](../tests/test_login.py#L110) |
| LOGIN-012 | Пустой email и только пробелы | По отдельности пустая строка и строка из пробелов | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_email](../tests/test_login.py#L178) [empty, spaces] |
| LOGIN-013 | Неверный формат email | userexample.com, user@, @example.com | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_email](../tests/test_login.py#L178) |
| LOGIN-014 | Пустой пароль | password = пустая строка | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_empty_password](../tests/test_login.py#L193) |
| LOGIN-015 | Регистр пароля значим | Войти с точным паролем, затем изменить регистр первой буквы | Исходный пароль — `200`; изменённый — `401 INVALID_CREDENTIALS` | Passed | [test_registered_password_is_case_sensitive](../tests/test_auth_flow.py#L115); сквозной сценарий |
| LOGIN-016 | Крайние пробелы пароля запрещены | Допустимый пароль с пробелом перед/после | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L269) |
| LOGIN-017 | Внутренний пробел пароля запрещён | `password 12345` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L269) |
| LOGIN-018 | Кириллический пароль запрещён | `ПарольДляТеста` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L269) |
| LOGIN-019 | Границы длины пароля при входе | 9, 10, 128, 129 букв a; для допустимых значений зарегистрировать пользователя | 9 и 129 — `422`; 10 и 128 — `200` | Passed | [test_login_with_invalid_password_length](../tests/test_login.py#L284); [test_register_and_login_with_allowed_ascii_password](../tests/test_auth_flow.py#L231) |
| LOGIN-020 | Границы длины email при входе | Зарегистрированный адрес длиной 254, включая крайние пробелы; адрес длиной 255 | 254 после обрезки — `200`; 255 — `422`, поле `body.email` | Passed | [test_register_and_login_with_max_email_length](../tests/test_auth_flow.py#L269); [test_login_with_email_exceeding_max_length](../tests/test_login.py#L296) |
| LOGIN-021 | Email вне ASCII запрещён | Кириллица в обеих частях, иероглифы, emoji | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_login_with_invalid_email_characters](../tests/test_login.py#L254) |
| LOGIN-022 | Пароль только из пробелов запрещён | 10 обычных пробелов | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L269); only_spaces |
| LOGIN-035 | Иероглифы и emoji в пароле запрещены | Существующий пользователь; пароль с символами вне ASCII | `422 VALIDATION_ERROR`, поле `body.password`; токен не выдаётся | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L269) |
| LOGIN-036 | Управляющие и невидимые символы пароля запрещены | Tab, LF, CR, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L269) |
| LOGIN-037 | Недопустимые пробелы и управляющие символы email | Внутренний пробел, Tab, LF, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_login_with_invalid_email_characters](../tests/test_login.py#L254) |
| LOGIN-038 | Пароль не требует сочетания категорий символов | Только буквы, цифры или пунктуация; полный набор печатных ASCII | С зарегистрированным паролем login `200` | Passed | [test_register_and_login_with_allowed_ascii_password](../tests/test_auth_flow.py#L231) |


## 3. Тело запроса

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-023 | Лишние поля | По одному добавить name, phone, role, is_active, password_hash, unexpected | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_extra_field](../tests/test_login.py#L137) |
| LOGIN-024 | Отсутствующее тело | POST без содержимого тела, Content-Type: application/json | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py#L166) [no_body] |
| LOGIN-025 | Пустой объект | Отправить {} | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py#L166) [empty_object] |
| LOGIN-026 | Сломанный JSON | Незавершённый объект | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py#L166) [malformed_json] |
| LOGIN-027 | Тело другого типа | null, массив, строка, число, boolean | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py#L166) |

## 4. Ошибки и отсутствие секретов

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-028 | Структура ошибки неверных учётных данных | Существующий пользователь; неверный пароль | `401 INVALID_CREDENTIALS`; тело соответствует ERROR_SCHEMA | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py#L208) |
| LOGIN-029 | Структура ошибки валидации | Короткий пароль Q7!x | `422 VALIDATION_ERROR`; тело соответствует ERROR_SCHEMA; details указывает body.password | Passed | [test_login_validation_error_response](../tests/test_login.py#L234) |
| LOGIN-030 | Идентификатор запроса в ошибках | Ответы 401 и 422 | Есть X-Request-ID, совпадает с error.request_id | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py#L208); [test_login_validation_error_response](../tests/test_login.py#L234) |
| LOGIN-031 | Заголовок авторизации при отказе | Неверный пароль | `401`; WWW-Authenticate = Bearer | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py#L208) |
| LOGIN-032 | Пароли и токен не раскрываются в ошибке входа | Получить токен; затем выполнить неуспешный вход с паролем-маркером | `401`; в теле нет исходного и переданного паролей, ранее выданного токена, access_token и password_hash | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py#L208) |
| LOGIN-033 | Секреты отсутствуют в ошибке валидации | Передать короткий пароль-маркер | `422`; в теле нет переданного пароля, access_token и password_hash | Passed | [test_login_validation_error_response](../tests/test_login.py#L234) |
| LOGIN-034 | Идентификатор успешного запроса | Успешный login | `200`; есть X-Request-ID | Not run | В текущем успешном тесте заголовок не проверяется |

ERROR_SCHEMA хранится в [schemas/error_response.py](../schemas/error_response.py) и импортируется обычным Python-импортом. Схема проверяет структуру; статусы, коды ошибок и значения проверяются assert внутри тестов.

## 5. Сквозные сценарии доступа

Эти пункты используют несколько операций и находятся в test_auth_flow.py.

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| AUTH-001 | Выданный токен открывает профиль | Зарегистрироваться, войти, вызвать GET /users/me с токеном | Login `200`; профиль `200`, данные соответствуют пользователю | Passed | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py#L8) |
| AUTH-002 | Деактивация закрывает доступ со старым токеном | Получить токен, убедиться в доступе, отключить пользователя, повторить GET /users/me | До отключения `200`; после — `401 UNAUTHORIZED` с тем же токеном | Passed | [test_disabled_user_cannot_use_existing_token](../tests/test_auth_flow.py#L134) |
| AUTH-003 | Реактивация восстанавливает доступ | Получить токен, отключить пользователя, проверить отказ, включить обратно | Старый ещё не истёкший токен снова открывает профиль; новый login с исходным паролем успешен | Passed | [test_reactivated_user_can_use_existing_token_and_login](../tests/test_auth_flow.py#L168) |

## Что оставили на следующий этап

- LOGIN-034: заголовок X-Request-ID успешного входа пока не проверяется. Границы полей login уже покрыты.
- Проверки изменения email профиля реализованы: [чек-лист профиля](profile-checklist.md).
- Отдельный блок авторизации: истёкший, подделанный и некорректный JWT; неверные iss/aud; отсутствие токена. Выдача непустой строки access_token и значение expires_in = 3600 сами по себе не подтверждают корректность содержимого и проверок JWT.

Существующие автотесты не доказывают полное покрытие login и авторизации. Сценарии в этом документе связаны с фактическими проверками кода; невыполненные проверки не отмечены Passed.
