# Чек-лист регистрации пользователя

> Последний полный HTTP-прогон от 03.11.2026: **329 passed за 46.53 с**, включая 105 случаев изменения профиля. Перенос данных и raw_body проверены этим прогоном. Локальный отчёт — `junit.xml`; commit запущенного приложения не зафиксирован.

**Операция:** `POST /api/v1/auth/register`  
**Окружение:** локальное API, `http://localhost:8000`  
**Дата составления:** 01.11.2026  
**Версия приложения / commit:** не зафиксирована  
**Дата ручного прогона:** не зафиксирована  
**Последний полный автопрогон:** 03.11.2026 — 329 passed за 46.53 с; HTTP-прогон обновлённого набора, отчёт `junit.xml`.

## Основания и статусы

- [FR-01 — пользователи и авторизация](requirements.md#fr-01-пользователи-и-авторизация).
- [Контракт API](api-specification.md): регистрация, формат ответа, ошибки и неизвестные поля.
- [Схема БД — users](database-schema.md#users).
- Живая OpenAPI-схема: `http://localhost:8000/openapi.json`, просмотрена 01.11.2026.

Статусы обновлены по полному HTTP-прогону 03.11.2026: 329 passed. Отчёт `junit.xml` создан локально и исключён из Git. Колонка «Автотест / покрытие» связывает пункт с тестом и указывает ограничения. Колонка подтверждений не используется.


- `Passed` — пункт покрыт прошедшими автотестами.
- `Partial` — прошла только часть проверки; оставшаяся часть указана в колонке покрытия.
- `Not run` — соответствующего автотеста нет; в этом прогоне пункт не выполнялся.
- `Требует уточнения` — ожидаемое поведение ещё не согласовано.
- `Failed` / `Blocked` — расхождение с ожиданием / препятствие выполнению; в текущем прогоне таких результатов нет.

Ранее наблюдавшийся приём кириллицы описывает прежнее поведение. Теперь символы вне ASCII в email/пароле запрещены: [решения к требованиям](registration-requirements-questions.md).

Тестовые данные в таблицах — примеры. Автотесты используют уникальные email и значения, указанные в коде. Для границ и разных типов смотрите конкретные параметры теста.

## Общие тестовые данные и правила выполнения

Базовый валидный запрос:

```json
{
  "email": "qa.reg.001@example.com",
  "password": "HotelDemo123!",
  "name": "Test User",
  "phone": "+79991234567"
}
```

- Для независимых регистраций использовать новый email, отсутствующий в БД. Исключение — проверки дубликатов.
- В негативном тесте менять только проверяемое поле, остальные оставлять валидными.
- Отправлять JSON с `Content-Type: application/json`.
- Для проверок длины повторять одну букву нужное количество раз. Для имени считать длину после обрезки крайних пробелов; для телефона считать цифры без `+`.
- В строках с несколькими значениями каждый вариант выполнять отдельным запросом. Общий `Passed` ставить только после прохождения всех вариантов.
- Для перенесённых проверок с неизвестными исходными данными сначала уточнить данные или повторить проверку: предложенные здесь примеры не являются свидетельством прошлого прогона.

Всего пунктов: 103; 83 Passed, 13 Partial, 7 Not run. Это покрытие пунктов, а не процент готовности продукта.

## 1. Основной сценарий и сохранение данных

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| REG-001 | Регистрация без телефона | Валидное тело без ключа `phone` | `201`; пользователь создан, `phone = null` | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| REG-002 | Регистрация с телефоном | Базовое тело | `201`; телефон соответствует переданному значению | Passed | [test_register_with_phone](../tests/test_registration.py#L26) |
| REG-003 | Роль нового пользователя | Успешная регистрация; ответ и запись БД | `role = user` | Partial | [test_register_without_phone](../tests/test_registration.py#L9); Проверен ответ API; БД в автотесте не проверяется |
| REG-004 | Активность нового пользователя | Успешная регистрация; ответ и запись БД | `is_active = true` | Partial | [test_register_without_phone](../tests/test_registration.py#L9); Проверен ответ API; БД в автотесте не проверяется |
| REG-005 | Пароль хранится в виде Argon2-хеша | Найти созданного пользователя в БД; проверить формат `users.password_hash`; при наличии инструмента — верификацию хеша | Вместо открытого пароля сохранён Argon2-хеш, соответствующий исходному паролю | Not run | Не автоматизировано; проверка Argon2 в БД отложена, планируется вручную |
| REG-007 | Регистрация публична | Валидное тело без заголовка Authorization | `201` | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| REG-008 | Основные данные пользователя в ответе регистрации | Валидная регистрация без телефона | `email` и `name` совпадают с отправленными; `phone = null`, `role = user`, `is_active = true` | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| REG-010 | Секреты отсутствуют в успешном ответе | Ответ регистрации | Нет `password` и `password_hash` | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| REG-011 | Вход после регистрации | Вызвать `/auth/login` с зарегистрированными email и паролем | `200`; выдан токен | Passed | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py#L8) |
| REG-012 | Чтение созданного профиля | С токеном из REG-011 вызвать `GET /users/me` | `200`; ID совпадает с регистрацией; профиль содержит сохранённые нормализованные значения | Passed | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py#L8); Проверены вход, поля профиля и совпадение ID с ответом регистрации |

## 2. Поле email

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| EMAIL-001 | Валидный email | Новый `qa.email.001@example.com` | `201`; email сохранён | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| EMAIL-002 | Приведение к нижнему регистру | Новый `QA.Email.002@EXAMPLE.COM` | `201`; в ответе и БД `qa.email.002@example.com` | Partial | [test_register_lowercases_email](../tests/test_registration.py#L163); Проверен ответ API; БД не проверяется |
| EMAIL-003 | Обрезка крайних пробелов | `"  qa.email.003@example.com  "` | `201`; в ответе и БД нет крайних пробелов | Partial | [test_register_trims_email](../tests/test_registration.py#L153); Проверен ответ API; БД не проверяется |
| EMAIL-004 | Дубликат email | Сначала создать пользователя, затем повторить его email | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py#L45) |
| EMAIL-005 | Обязательность поля | Удалить ключ `email` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py#L60) |
| EMAIL-006 | Пустая строка | `"email": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_email](../tests/test_registration.py#L178) |
| EMAIL-007 | Максимальная длина | Корректный по формату email длиной 254 символа | `201` | Passed | [test_register_with_max_email_length](../tests/test_registration.py#L228) |
| EMAIL-008 | Дубликат в другом регистре | Существующий email передать в другом регистре | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py#L45) |
| EMAIL-009 | Дубликат с крайними пробелами | Существующий email окружить пробелами | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py#L45) |
| EMAIL-010 | Превышение максимальной длины | Email длиной 255 символов, без иных нарушений формата, насколько это возможно | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_email_exceeding_max_length](../tests/test_registration.py#L239) |
| EMAIL-011 | Неверный формат | По отдельности: `userexample.com`, `user@`, `@example.com` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_email](../tests/test_registration.py#L178) |
| EMAIL-012 | Неверный тип | Число / boolean; исходный набор значений уточнить | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L213) |
| EMAIL-013 | Явный null | `"email": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py#L193) |
| EMAIL-014 | Только пробелы | `"email": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_email](../tests/test_registration.py#L178) |
| EMAIL-015 | Массив и объект | По отдельности: `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L213) |
| EMAIL-016 | Комбинация нормализации при дубликате | Существующий email одновременно в другом регистре и с пробелами по краям | `409`, `error.code = EMAIL_EXISTS` | Not run | Не автоматизировано |
| EMAIL-017 | Кириллица до @ запрещена | `пользователь@example.com` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414); cyrillic_local |
| EMAIL-018 | Кириллица после @ запрещена | `user@пример.рф` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414); cyrillic_domain |
| EMAIL-019 | Кириллица в обеих частях запрещена | `пользователь@пример.рф` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414); cyrillic_both |
| EMAIL-020 | Крайние пробелы не скрывают Unicode в email | `"  ПОЛЬЗОВАТЕЛЬ@ПРИМЕР.РФ  "` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414); cyrillic_with_outer_spaces |
| EMAIL-021 | Смешение латиницы и кириллицы запрещено | `usеr@example.com` — кириллическая е | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414); mixed_script |
| EMAIL-022 | Вход с email вне ASCII запрещён | Email с кириллицей до/после @ | `422 VALIDATION_ERROR`, поле `body.email`; токен не выдаётся | Passed | [test_login_with_invalid_email_characters](../tests/test_login.py#L248) |
| EMAIL-023 | Иероглифы и emoji в обеих частях email запрещены | Иероглифы/emoji до @ и в домене | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414) |
| EMAIL-024 | Управляющие и невидимые символы email запрещены | Tab, LF, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.email`; символы не удаляются | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414) |
| EMAIL-025 | Внутренний пробел email запрещён | `user name@example.com` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py#L414) |
| EMAIL-026 | Максимальная длина считается после обрезки | Email 254 символа с крайними обычными пробелами | Регистрация `201`; нормализованный адрес длиной 254; login `200` | Passed | [test_register_and_login_with_max_email_length](../tests/test_auth_flow.py#L261) |
| EMAIL-027 | ASCII email с plus-tag и Punycode | Уникальная локальная часть +tag, домены example.com и xn--e1afmkfd.xn--p1ai | Регистрация `201`; email нормализован; login `200` | Passed | [test_register_and_login_with_ascii_email](../tests/test_auth_flow.py#L242) |

Пример подготовки длинного адреса: 64 символа `a`, затем `@`, затем домен из меток длиной 63, 63 и 61, разделённых точками — всего 254 символа. Для 255 увеличить последнюю метку до 62. В протоколе прогона сохранить получившиеся строки. Проверять, что причина отказа относится к исследуемому ограничению, а не к другому правилу email.


## 3. Поле password

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| PASS-001 | Валидный пароль | `HotelDemo123!` | `201` | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| PASS-002 | Пробелы в пароле запрещены | Крайние, внутренние и только пробелы | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-003 | Пароль короче минимума | Строка длиной менее 10; исходная длина не зафиксирована | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L76) |
| PASS-004 | Пароль длиннее максимума | Строка длиной более 128; исходная длина не зафиксирована | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L76) |
| PASS-005 | Обязательность поля | Удалить ключ `password` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py#L60) |
| PASS-006 | Неверный тип | Число / boolean; исходный набор значений уточнить | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L213) |
| PASS-007 | Точные границы | По отдельности: 9, 10, 128, 129 символов | Соответственно `422`, `error.code = VALIDATION_ERROR` / `201` / `201` / `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L76); Также test_register_with_valid_password_length: вместе проверены 9, 10, 128 и 129 |
| PASS-008 | Пустая строка | `"password": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L76) |
| PASS-009 | Явный null | `"password": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py#L193) |
| PASS-010 | Массив и объект | По отдельности: `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L213) |
| PASS-011 | Крайние пробелы пароля отклоняются | Пробел перед/после допустимого пароля | `422 VALIDATION_ERROR`, пароль не обрезается | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-012 | Внутренний пробел пароля отклоняется | `password 12345` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-013 | Кириллический пароль отклоняется | `ПарольДляТеста` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-014 | Вход с кириллическим паролем отклоняется | Существующий пользователь; `ПарольДляТеста` | `422 VALIDATION_ERROR`, поле `body.password`; токен не выдаётся | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L263) |
| PASS-015 | Смешанный кириллический/латинский пароль запрещён | `ПарольTest123` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-016 | Кириллическая буква вместо латинской запрещена при входе | `TestPassword123а` — кириллическая а | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py#L263); confusable |
| PASS-017 | Кириллица запрещена при допустимой длине | 10 и 128 букв я | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-018 | Иероглифы и emoji в пароле запрещены | ASCII-пароль с иероглифами/emoji, общая длина допустима | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-019 | Управляющие и невидимые символы пароля запрещены | Tab, LF, CR, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428) |
| PASS-020 | Пароль только из пробелов запрещён | 10 обычных пробелов | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py#L428); only_spaces |
| PASS-021 | Нет обязательного сочетания категорий символов | Только буквы; только цифры; только пунктуация; все печатные ASCII без пробела | Регистрация `201`; login `200`; непустой токен | Passed | [test_register_and_login_with_allowed_ascii_password](../tests/test_auth_flow.py#L224) |


## 4. Поле name

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| NAME-001 | Валидное имя | `Test User` | `201`; имя сохранено | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| NAME-002 | Обрезка крайних пробелов | `"  Test User  "` | `201`; в ответе и БД `Test User` | Partial | [test_register_trims_name](../tests/test_registration.py#L139); Проверен ответ API; БД не проверяется |
| NAME-003 | Пустое имя | `"name": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py#L105) |
| NAME-004 | Имя пустое после обрезки | `"name": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py#L105) |
| NAME-005 | Минимальная допустимая длина | `"name": "A"` | `201` | Passed | [test_register_with_valid_name_length](../tests/test_registration.py#L121) |
| NAME-006 | Максимальная допустимая длина | 100 символов `a` | `201` | Passed | [test_register_with_valid_name_length](../tests/test_registration.py#L121) |
| NAME-007 | Превышение максимальной длины | 101 символ `a` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py#L105) |
| NAME-008 | Длина проверяется после обрезки | 100 символов `a`, окружённых двумя пробелами с каждой стороны | `201`; сохранены 100 символов без крайних пробелов | Passed | [test_register_trims_name](../tests/test_registration.py#L139) |
| NAME-009 | Обязательность поля | Удалить ключ `name` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py#L60) |
| NAME-010 | Неверные типы | По отдельности: `123`, `true`, `false`, `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L213) |
| NAME-011 | Явный null | `"name": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py#L193) |
| NAME-012 | Кириллица | `Евгений` | `201`; имя сохранено корректно | Passed | [test_register_with_cyrillic_name](../tests/test_registration.py#L404) |

## 5. Поле phone

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| PHONE-001 | Корректный телефон | `+79991234567` | `201`; значение сохранено | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L257); Используются граничные номера, а не точный пример строки чек-листа |
| PHONE-002 | Явный null | `"phone": null` | `201`; `phone = null` в ответе и БД | Partial | [test_register_with_null_phone](../tests/test_registration.py#L282); Проверен ответ API; БД не проверяется |
| PHONE-003 | Пустая строка | `"phone": ""` | `422`, `error.code = VALIDATION_ERROR` по OpenAPI; пустая строка не равна null | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L318) |
| PHONE-004 | Только пробелы | `"phone": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L318) |
| PHONE-005 | Телефон без плюса | `79991234567` как JSON-строка | `201`; значение соответствует переданному | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L257); Используются граничные номера, а не точный пример строки чек-листа |
| PHONE-006 | Другой начальный код | `+441234567890` | `201`; ограничения на код страны нет | Not run | Не автоматизировано |
| PHONE-007 | Меньше минимума | 6 цифр без плюса и отдельно с плюсом | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone_length](../tests/test_registration.py#L268) |
| PHONE-008 | Минимальная длина | 7 цифр без плюса и отдельно с плюсом | `201` | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L257) |
| PHONE-009 | Максимальная длина | 15 цифр без плюса и отдельно с плюсом | `201`; плюс не входит в количество цифр | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L257) |
| PHONE-010 | Превышение максимума | 16 цифр без плюса и отдельно с плюсом | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone_length](../tests/test_registration.py#L268) |
| PHONE-011 | Неверные типы | По отдельности: `1234567890` как число, `true`, `false`, `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L213); Проверены типы и указание ошибочного поля; число при преобразовании в строку укладывается в допустимую длину телефона |
| PHONE-012 | Буквы | `+7999abc4567` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L318) |
| PHONE-013 | Дефисы, скобки, внутренние пробелы | По отдельности: `7999-1234567`, `(7999)1234567`, `7999 1234567` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L318) |
| PHONE-014 | Неверное положение или количество плюсов | По отдельности: `++79991234567`, `79991234567+` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L318) |
| PHONE-015 | Цифры вне ASCII | `１２３４５６７` — полноширинные цифры | `422`, `error.code = VALIDATION_ERROR`: шаблон допускает только `[0-9]` | Not run | Не автоматизировано |
| PHONE-016 | Кириллица в телефоне | `+7999абв4567` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L318) |

Отсутствие телефона покрыто REG-001. Явный null проверяется отдельно в PHONE-002.

## 6. Тело запроса и защита серверных полей

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| BODY-001 | Назначение роли клиентом запрещено | Добавить к валидному телу `"role": "admin"` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py#L345); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-002 | Изменение активности клиентом запрещено | Добавить `"is_active": false` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py#L345); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-003 | Передача хеша запрещена | Добавить `"password_hash": "some-value"` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py#L345); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-004 | Произвольное неизвестное поле запрещено | Добавить `"unexpected": "value"` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_extra_field](../tests/test_registration.py#L345) |
| BODY-005 | Передача серверных идентификатора и времени запрещена | По одному добавлять `id`, `created_at`, `updated_at` с корректными по формату значениями | `422`, `error.code = VALIDATION_ERROR` для каждого поля | Passed | [test_register_with_extra_field](../tests/test_registration.py#L345) |
| BODY-006 | Пустой JSON-объект | `{}` | `422`, `error.code = VALIDATION_ERROR`; указаны ошибки обязательных полей | Partial | [test_register_with_invalid_body](../tests/test_registration.py#L364); Проверены 422 и code; состав ошибок обязательных полей здесь не проверяется |
| BODY-007 | Отсутствие тела | Отправить POST без тела | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_body](../tests/test_registration.py#L364) |
| BODY-008 | Тело не является объектом | По отдельности: `null`, `[]`, `"text"`, `123`, `true` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Not run | Не автоматизировано |
| BODY-009 | Синтаксически неверный JSON | Например, отсутствует закрывающая фигурная скобка | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_body](../tests/test_registration.py#L364) |

## 7. Ошибки, отсутствие побочных изменений и конкуренция

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| RESP-001 | Единый формат ошибки валидации | Передать короткий пароль `Q7!x` | `422`, `error.code = VALIDATION_ERROR`; объект `error` содержит `code`, `message`, `details`, `request_id`; элементы details содержат `field`, `message`, `type` | Passed | [test_register_validation_error_response](../tests/test_registration.py#L371) |
| RESP-002 | Единый формат конфликта email | Повторить регистрацию существующего email | `409`, `error.code = EMAIL_EXISTS`; присутствуют `error.message`, `details`, `request_id` | Passed | [test_register_duplicate_email_error_response](../tests/test_registration.py#L389) |
| RESP-003 | Идентификатор запроса | Проверить ответы `201`, `409`, `422` | В каждом есть серверный заголовок `X-Request-ID` | Partial | [test_register_validation_error_response](../tests/test_registration.py#L371); Также test_register_duplicate_email_error_response; заголовок проверен для 422 и 409, для 201 ещё нет |
| RESP-004 | Пароль не раскрывается в ошибках | Передать узнаваемый пароль-маркер; вызвать 422, затем отдельно 409 | Ответы не содержат переданный пароль, хеш или полное исходное тело с секретами | Passed | [test_register_validation_error_response](../tests/test_registration.py#L371); Также test_register_duplicate_email_error_response; проверены пароль-маркер и отсутствие password_hash, без чтения БД |
| DATA-001 | Отказ валидации не создаёт пользователя | Новый email; невалидное имя; сравнить БД до и после | `422`, `error.code = VALIDATION_ERROR`; запись с новым email отсутствует | Partial | [test_rejected_registration_does_not_reserve_email](../tests/test_auth_flow.py#L80); Проверены отказ входа и последующая регистрация того же email; отсутствие строки в БД напрямую не проверяется |
| DATA-002 | Конфликт не изменяет существующего пользователя | Существующий email; другие валидные name, phone и password | `409`, `error.code = EMAIL_EXISTS`; поля существующей записи и хеш не изменились; новых записей нет | Partial | [test_duplicate_registration_does_not_change_user](../tests/test_auth_flow.py#L40); Проверены имя, email и работа старого пароля; phone, хеш и количество записей в БД не проверяются |
| DATA-003 | Создаётся ровно один пользователь | Валидная регистрация; сравнить БД до и после | `201`; одна новая запись с ID из ответа | Not run | Не автоматизировано |
| CONC-001 | Одновременная регистрация одного email | Два параллельных валидных запроса с одинаковым новым email | Один `201`, другой `409`, `error.code = EMAIL_EXISTS`; в БД одна запись; нет `500` | Not run | Не автоматизировано; конкурентный сценарий отложен |

## Уточнения перед следующим прогоном

- Решения по символам email/пароля и порядку проверки длины email зафиксированы в [решениях к требованиям регистрации](registration-requirements-questions.md). Проверки регистрации и входа адаптированы; статусы отражают новый прогон. Проверки изменения email профиля добавлены: [чек-лист профиля](profile-checklist.md).
- Дата последнего подтверждённого прогона — 03.11.2026. Версия приложения для него не зафиксирована; при следующем прогоне сохранить commit/образ приложения и отчёт. Не сохранять в публичном портфолио действующие токены или реальные учётные данные.

## Что осталось

- Проверки изменения email профиля, включая отсутствие изменений при отказе, реализованы: [чек-лист профиля](profile-checklist.md).
- Вручную проверить Argon2 в БД (REG-005); автоматизацию БД пока отложили.
- Конкурентную регистрацию (CONC-001) выполнить позже.
- При необходимости дополнить заголовок для 201 и проверки БД; сравнение ID регистрации и профиля уже проверено.
- Пока не автоматизированы: комбинация регистра и пробелов в дубликате email (EMAIL-016), другой код страны (PHONE-006), полноширинные цифры (PHONE-015), тело другого типа (BODY-008), точное количество записей в БД (DATA-003).

## Дополнительные выполненные сценарии

- [test_registered_password_is_case_sensitive](../tests/test_auth_flow.py#L112): исходный пароль позволяет войти, изменение регистра первой буквы даёт 401 INVALID_CREDENTIALS.
- [test_rejected_registration_does_not_reserve_email](../tests/test_auth_flow.py#L80): после 422 вход невозможен, исправленная регистрация с тем же email успешна. Это проверка через API, без SQL.

Один пункт чек-листа может соответствовать нескольким запускам параметризованного теста, а один тест — нескольким пунктам. Поэтому 329 passed по проекту не означает 329 полностью закрытых пунктов этого чек-листа.
