# Пользователи и авторизация

Сценарии, ограничения и связь с автотестами. ID проверок сохранены. Число пунктов не равно числу параметризованных случаев. Последний полный прогон: **519 passed за 189.45 с**; [журнал](test-runs.md). Passed / Partial / Not run описывают объём проверки пункта: успешный прогон набора не закрывает непокрытые части. Исторические сведения о версиях и результаты отдельных этапов вынесены в журнал.

- [Чек-лист регистрации пользователя](#registration-checklist)
- [Чек-лист входа пользователя](#login-checklist)
- [Чек-лист изменения профиля](#profile-checklist)
- [Решения и открытые вопросы к требованиям регистрации](#registration-requirements-questions)

<a id="registration-checklist"></a>

## Чек-лист регистрации пользователя

<a id="registration-checklist-основания-и-статусы"></a>

### Основания и статусы

- [FR-01 — пользователи и авторизация](requirements.md#fr-01-пользователи-и-авторизация).
- [Контракт API](api-specification.md): регистрация, формат ответа, ошибки и неизвестные поля.
- [Схема БД — users](database-schema.md#users).
- Живая OpenAPI-схема: `http://localhost:8000/openapi.json`, просмотрена 01.11.2026.

Ранее наблюдавшийся приём кириллицы описывает прежнее поведение. Теперь символы вне ASCII в email/пароле запрещены: [решения к требованиям](testing-auth.md#registration-requirements-questions).

Тестовые данные в таблицах — примеры. Автотесты используют уникальные email и значения, указанные в коде. Для границ и разных типов смотрите конкретные параметры теста.

<a id="registration-checklist-общие-тестовые-данные-и-правила-выполнения"></a>

### Общие тестовые данные и правила выполнения

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

<a id="registration-checklist-1-основной-сценарий-и-сохранение-данных"></a>

### 1. Основной сценарий и сохранение данных

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| REG-001 | Регистрация без телефона | Валидное тело без ключа `phone` | `201`; пользователь создан, `phone = null` | Passed | [test_register_without_phone](../tests/test_registration.py) |
| REG-002 | Регистрация с телефоном | Базовое тело | `201`; телефон соответствует переданному значению | Passed | [test_register_with_phone](../tests/test_registration.py) |
| REG-003 | Роль нового пользователя | Успешная регистрация; ответ и запись БД | `role = user` | Partial | [test_register_without_phone](../tests/test_registration.py); Проверен ответ API; БД в автотесте не проверяется |
| REG-004 | Активность нового пользователя | Успешная регистрация; ответ и запись БД | `is_active = true` | Partial | [test_register_without_phone](../tests/test_registration.py); Проверен ответ API; БД в автотесте не проверяется |
| REG-005 | Пароль хранится в виде Argon2-хеша | Найти созданного пользователя в БД; проверить формат `users.password_hash`; при наличии инструмента — верификацию хеша | Вместо открытого пароля сохранён Argon2-хеш, соответствующий исходному паролю | Not run | Не автоматизировано; проверка Argon2 в БД отложена, планируется вручную |
| REG-007 | Регистрация публична | Валидное тело без заголовка Authorization | `201` | Passed | [test_register_without_phone](../tests/test_registration.py) |
| REG-008 | Основные данные пользователя в ответе регистрации | Валидная регистрация без телефона | `email` и `name` совпадают с отправленными; `phone = null`, `role = user`, `is_active = true` | Passed | [test_register_without_phone](../tests/test_registration.py) |
| REG-010 | Секреты отсутствуют в успешном ответе | Ответ регистрации | Нет `password` и `password_hash` | Passed | [test_register_without_phone](../tests/test_registration.py) |
| REG-011 | Вход после регистрации | Вызвать `/auth/login` с зарегистрированными email и паролем | `200`; выдан токен | Passed | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py) |
| REG-012 | Чтение созданного профиля | С токеном из REG-011 вызвать `GET /users/me` | `200`; ID совпадает с регистрацией; профиль содержит сохранённые нормализованные значения | Passed | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py); Проверены вход, поля профиля и совпадение ID с ответом регистрации |

<a id="registration-checklist-2-поле-email"></a>

### 2. Поле email

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| EMAIL-001 | Валидный email | Новый `qa.email.001@example.com` | `201`; email сохранён | Passed | [test_register_without_phone](../tests/test_registration.py) |
| EMAIL-002 | Приведение к нижнему регистру | Новый `QA.Email.002@EXAMPLE.COM` | `201`; в ответе и БД `qa.email.002@example.com` | Partial | [test_register_lowercases_email](../tests/test_registration.py); Проверен ответ API; БД не проверяется |
| EMAIL-003 | Обрезка крайних пробелов | `"  qa.email.003@example.com  "` | `201`; в ответе и БД нет крайних пробелов | Partial | [test_register_trims_email](../tests/test_registration.py); Проверен ответ API; БД не проверяется |
| EMAIL-004 | Дубликат email | Сначала создать пользователя, затем повторить его email | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py) |
| EMAIL-005 | Обязательность поля | Удалить ключ `email` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py) |
| EMAIL-006 | Пустая строка | `"email": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_email](../tests/test_registration.py) |
| EMAIL-007 | Максимальная длина | Корректный по формату email длиной 254 символа | `201` | Passed | [test_register_with_max_email_length](../tests/test_registration.py) |
| EMAIL-008 | Дубликат в другом регистре | Существующий email передать в другом регистре | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py) |
| EMAIL-009 | Дубликат с крайними пробелами | Существующий email окружить пробелами | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py) |
| EMAIL-010 | Превышение максимальной длины | Email длиной 255 символов, без иных нарушений формата, насколько это возможно | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_email_exceeding_max_length](../tests/test_registration.py) |
| EMAIL-011 | Неверный формат | По отдельности: `userexample.com`, `user@`, `@example.com` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_email](../tests/test_registration.py) |
| EMAIL-012 | Неверный тип | Число / boolean; исходный набор значений уточнить | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py) |
| EMAIL-013 | Явный null | `"email": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py) |
| EMAIL-014 | Только пробелы | `"email": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_email](../tests/test_registration.py) |
| EMAIL-015 | Массив и объект | По отдельности: `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py) |
| EMAIL-016 | Комбинация нормализации при дубликате | Существующий email одновременно в другом регистре и с пробелами по краям | `409`, `error.code = EMAIL_EXISTS` | Not run | Не автоматизировано |
| EMAIL-017 | Кириллица до @ запрещена | `пользователь@example.com` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py); cyrillic_local |
| EMAIL-018 | Кириллица после @ запрещена | `user@пример.рф` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py); cyrillic_domain |
| EMAIL-019 | Кириллица в обеих частях запрещена | `пользователь@пример.рф` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py); cyrillic_both |
| EMAIL-020 | Крайние пробелы не скрывают Unicode в email | `"  ПОЛЬЗОВАТЕЛЬ@ПРИМЕР.РФ  "` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py); cyrillic_with_outer_spaces |
| EMAIL-021 | Смешение латиницы и кириллицы запрещено | `usеr@example.com` — кириллическая е | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py); mixed_script |
| EMAIL-022 | Вход с email вне ASCII запрещён | Email с кириллицей до/после @ | `422 VALIDATION_ERROR`, поле `body.email`; токен не выдаётся | Passed | [test_login_with_invalid_email_characters](../tests/test_login.py) |
| EMAIL-023 | Иероглифы и emoji в обеих частях email запрещены | Иероглифы/emoji до @ и в домене | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py) |
| EMAIL-024 | Управляющие и невидимые символы email запрещены | Tab, LF, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.email`; символы не удаляются | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py) |
| EMAIL-025 | Внутренний пробел email запрещён | `user name@example.com` | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_register_with_invalid_email_characters](../tests/test_registration.py) |
| EMAIL-026 | Максимальная длина считается после обрезки | Email 254 символа с крайними обычными пробелами | Регистрация `201`; нормализованный адрес длиной 254; login `200` | Passed | [test_register_and_login_with_max_email_length](../tests/test_auth_flow.py) |
| EMAIL-027 | ASCII email с plus-tag и Punycode | Уникальная локальная часть +tag, домены example.com и xn--e1afmkfd.xn--p1ai | Регистрация `201`; email нормализован; login `200` | Passed | [test_register_and_login_with_ascii_email](../tests/test_auth_flow.py) |

Пример подготовки длинного адреса: 64 символа `a`, затем `@`, затем домен из меток длиной 63, 63 и 61, разделённых точками — всего 254 символа. Для 255 увеличить последнюю метку до 62. В протоколе прогона сохранить получившиеся строки. Проверять, что причина отказа относится к исследуемому ограничению, а не к другому правилу email.


<a id="registration-checklist-3-поле-password"></a>

### 3. Поле password

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| PASS-001 | Валидный пароль | `HotelDemo123!` | `201` | Passed | [test_register_without_phone](../tests/test_registration.py) |
| PASS-002 | Пробелы в пароле запрещены | Крайние, внутренние и только пробелы | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-003 | Пароль короче минимума | Строка длиной менее 10; исходная длина не зафиксирована | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py) |
| PASS-004 | Пароль длиннее максимума | Строка длиной более 128; исходная длина не зафиксирована | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py) |
| PASS-005 | Обязательность поля | Удалить ключ `password` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py) |
| PASS-006 | Неверный тип | Число / boolean; исходный набор значений уточнить | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py) |
| PASS-007 | Точные границы | По отдельности: 9, 10, 128, 129 символов | Соответственно `422`, `error.code = VALIDATION_ERROR` / `201` / `201` / `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py); Также test_register_with_valid_password_length: вместе проверены 9, 10, 128 и 129 |
| PASS-008 | Пустая строка | `"password": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py) |
| PASS-009 | Явный null | `"password": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py) |
| PASS-010 | Массив и объект | По отдельности: `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py) |
| PASS-011 | Крайние пробелы пароля отклоняются | Пробел перед/после допустимого пароля | `422 VALIDATION_ERROR`, пароль не обрезается | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-012 | Внутренний пробел пароля отклоняется | `password 12345` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-013 | Кириллический пароль отклоняется | `ПарольДляТеста` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-014 | Вход с кириллическим паролем отклоняется | Существующий пользователь; `ПарольДляТеста` | `422 VALIDATION_ERROR`, поле `body.password`; токен не выдаётся | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py) |
| PASS-015 | Смешанный кириллический/латинский пароль запрещён | `ПарольTest123` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-016 | Кириллическая буква вместо латинской запрещена при входе | `TestPassword123а` — кириллическая а | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py); confusable |
| PASS-017 | Кириллица запрещена при допустимой длине | 10 и 128 букв я | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-018 | Иероглифы и emoji в пароле запрещены | ASCII-пароль с иероглифами/emoji, общая длина допустима | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-019 | Управляющие и невидимые символы пароля запрещены | Tab, LF, CR, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py) |
| PASS-020 | Пароль только из пробелов запрещён | 10 обычных пробелов | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_register_with_invalid_password_characters](../tests/test_registration.py); only_spaces |
| PASS-021 | Нет обязательного сочетания категорий символов | Только буквы; только цифры; только пунктуация; все печатные ASCII без пробела | Регистрация `201`; login `200`; непустой токен | Passed | [test_register_and_login_with_allowed_ascii_password](../tests/test_auth_flow.py) |


<a id="registration-checklist-4-поле-name"></a>

### 4. Поле name

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| NAME-001 | Валидное имя | `Test User` | `201`; имя сохранено | Passed | [test_register_without_phone](../tests/test_registration.py) |
| NAME-002 | Обрезка крайних пробелов | `"  Test User  "` | `201`; в ответе и БД `Test User` | Partial | [test_register_trims_name](../tests/test_registration.py); Проверен ответ API; БД не проверяется |
| NAME-003 | Пустое имя | `"name": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py) |
| NAME-004 | Имя пустое после обрезки | `"name": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py) |
| NAME-005 | Минимальная допустимая длина | `"name": "A"` | `201` | Passed | [test_register_with_valid_name_length](../tests/test_registration.py) |
| NAME-006 | Максимальная допустимая длина | 100 символов `a` | `201` | Passed | [test_register_with_valid_name_length](../tests/test_registration.py) |
| NAME-007 | Превышение максимальной длины | 101 символ `a` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py) |
| NAME-008 | Длина проверяется после обрезки | 100 символов `a`, окружённых двумя пробелами с каждой стороны | `201`; сохранены 100 символов без крайних пробелов | Passed | [test_register_trims_name](../tests/test_registration.py) |
| NAME-009 | Обязательность поля | Удалить ключ `name` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py) |
| NAME-010 | Неверные типы | По отдельности: `123`, `true`, `false`, `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py) |
| NAME-011 | Явный null | `"name": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py) |
| NAME-012 | Кириллица | `Евгений` | `201`; имя сохранено корректно | Passed | [test_register_with_cyrillic_name](../tests/test_registration.py) |

<a id="registration-checklist-5-поле-phone"></a>

### 5. Поле phone

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| PHONE-001 | Корректный телефон | `+79991234567` | `201`; значение сохранено | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py); Используются граничные номера, а не точный пример строки чек-листа |
| PHONE-002 | Явный null | `"phone": null` | `201`; `phone = null` в ответе и БД | Partial | [test_register_with_null_phone](../tests/test_registration.py); Проверен ответ API; БД не проверяется |
| PHONE-003 | Пустая строка | `"phone": ""` | `422`, `error.code = VALIDATION_ERROR` по OpenAPI; пустая строка не равна null | Passed | [test_register_with_invalid_phone](../tests/test_registration.py) |
| PHONE-004 | Только пробелы | `"phone": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py) |
| PHONE-005 | Телефон без плюса | `79991234567` как JSON-строка | `201`; значение соответствует переданному | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py); Используются граничные номера, а не точный пример строки чек-листа |
| PHONE-006 | Другой начальный код | `+441234567890` | `201`; ограничения на код страны нет | Not run | Не автоматизировано |
| PHONE-007 | Меньше минимума | 6 цифр без плюса и отдельно с плюсом | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone_length](../tests/test_registration.py) |
| PHONE-008 | Минимальная длина | 7 цифр без плюса и отдельно с плюсом | `201` | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py) |
| PHONE-009 | Максимальная длина | 15 цифр без плюса и отдельно с плюсом | `201`; плюс не входит в количество цифр | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py) |
| PHONE-010 | Превышение максимума | 16 цифр без плюса и отдельно с плюсом | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone_length](../tests/test_registration.py) |
| PHONE-011 | Неверные типы | По отдельности: `1234567890` как число, `true`, `false`, `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py); Проверены типы и указание ошибочного поля; число при преобразовании в строку укладывается в допустимую длину телефона |
| PHONE-012 | Буквы | `+7999abc4567` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py) |
| PHONE-013 | Дефисы, скобки, внутренние пробелы | По отдельности: `7999-1234567`, `(7999)1234567`, `7999 1234567` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_phone](../tests/test_registration.py) |
| PHONE-014 | Неверное положение или количество плюсов | По отдельности: `++79991234567`, `79991234567+` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_phone](../tests/test_registration.py) |
| PHONE-015 | Цифры вне ASCII | `１２３４５６７` — полноширинные цифры | `422`, `error.code = VALIDATION_ERROR`: шаблон допускает только `[0-9]` | Not run | Не автоматизировано |
| PHONE-016 | Кириллица в телефоне | `+7999абв4567` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py) |

Отсутствие телефона покрыто REG-001. Явный null проверяется отдельно в PHONE-002.

<a id="registration-checklist-6-тело-запроса-и-защита-серверных-полей"></a>

### 6. Тело запроса и защита серверных полей

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| BODY-001 | Назначение роли клиентом запрещено | Добавить к валидному телу `"role": "admin"` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-002 | Изменение активности клиентом запрещено | Добавить `"is_active": false` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-003 | Передача хеша запрещена | Добавить `"password_hash": "some-value"` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-004 | Произвольное неизвестное поле запрещено | Добавить `"unexpected": "value"` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_extra_field](../tests/test_registration.py) |
| BODY-005 | Передача серверных идентификатора и времени запрещена | По одному добавлять `id`, `created_at`, `updated_at` с корректными по формату значениями | `422`, `error.code = VALIDATION_ERROR` для каждого поля | Passed | [test_register_with_extra_field](../tests/test_registration.py) |
| BODY-006 | Пустой JSON-объект | `{}` | `422`, `error.code = VALIDATION_ERROR`; указаны ошибки обязательных полей | Partial | [test_register_with_invalid_body](../tests/test_registration.py); Проверены 422 и code; состав ошибок обязательных полей здесь не проверяется |
| BODY-007 | Отсутствие тела | Отправить POST без тела | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_body](../tests/test_registration.py) |
| BODY-008 | Тело не является объектом | По отдельности: `null`, `[]`, `"text"`, `123`, `true` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Not run | Не автоматизировано |
| BODY-009 | Синтаксически неверный JSON | Например, отсутствует закрывающая фигурная скобка | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_body](../tests/test_registration.py) |

<a id="registration-checklist-7-ошибки-отсутствие-побочных-изменений-и-конкуренция"></a>

### 7. Ошибки, отсутствие побочных изменений и конкуренция

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| RESP-001 | Единый формат ошибки валидации | Передать короткий пароль `Q7!x` | `422`, `error.code = VALIDATION_ERROR`; объект `error` содержит `code`, `message`, `details`, `request_id`; элементы details содержат `field`, `message`, `type` | Passed | [test_register_validation_error_response](../tests/test_registration.py) |
| RESP-002 | Единый формат конфликта email | Повторить регистрацию существующего email | `409`, `error.code = EMAIL_EXISTS`; присутствуют `error.message`, `details`, `request_id` | Passed | [test_register_duplicate_email_error_response](../tests/test_registration.py) |
| RESP-003 | Идентификатор запроса | Проверить ответы `201`, `409`, `422` | В каждом есть серверный заголовок `X-Request-ID` | Partial | [test_register_validation_error_response](../tests/test_registration.py); Также test_register_duplicate_email_error_response; заголовок проверен для 422 и 409, для 201 ещё нет |
| RESP-004 | Пароль не раскрывается в ошибках | Передать узнаваемый пароль-маркер; вызвать 422, затем отдельно 409 | Ответы не содержат переданный пароль, хеш или полное исходное тело с секретами | Passed | [test_register_validation_error_response](../tests/test_registration.py); Также test_register_duplicate_email_error_response; проверены пароль-маркер и отсутствие password_hash, без чтения БД |
| DATA-001 | Отказ валидации не создаёт пользователя | Новый email; невалидное имя; сравнить БД до и после | `422`, `error.code = VALIDATION_ERROR`; запись с новым email отсутствует | Partial | [test_rejected_registration_does_not_reserve_email](../tests/test_auth_flow.py); Проверены отказ входа и последующая регистрация того же email; отсутствие строки в БД напрямую не проверяется |
| DATA-002 | Конфликт не изменяет существующего пользователя | Существующий email; другие валидные name, phone и password | `409`, `error.code = EMAIL_EXISTS`; поля существующей записи и хеш не изменились; новых записей нет | Partial | [test_duplicate_registration_does_not_change_user](../tests/test_auth_flow.py); Проверены имя, email и работа старого пароля; phone, хеш и количество записей в БД не проверяются |
| DATA-003 | Создаётся ровно один пользователь | Валидная регистрация; сравнить БД до и после | `201`; одна новая запись с ID из ответа | Not run | Не автоматизировано |
| CONC-001 | Одновременная регистрация одного email | Два параллельных валидных запроса с одинаковым новым email | Один `201`, другой `409`, `error.code = EMAIL_EXISTS`; в БД одна запись; нет `500` | Not run | Не автоматизировано; конкурентный сценарий отложен |

<a id="registration-checklist-уточнения-перед-следующим-прогоном"></a>

### Уточнения перед следующим прогоном

- Решения по символам email/пароля и порядку проверки длины email зафиксированы в [решениях к требованиям регистрации](testing-auth.md#registration-requirements-questions). Проверки регистрации и входа адаптированы; статусы отражают новый прогон. Проверки изменения email профиля добавлены: [чек-лист профиля](testing-auth.md#profile-checklist).
- Полный прогон и идентификация стенда зафиксированы в [журнале](test-runs.md). При следующих прогонах сохранять commit/образ приложения и результат. Не сохранять в публичном портфолио действующие токены или реальные учётные данные.

<a id="registration-checklist-что-осталось"></a>

### Что осталось

- Проверки изменения email профиля, включая отсутствие изменений при отказе, реализованы: [чек-лист профиля](testing-auth.md#profile-checklist).
- Вручную проверить Argon2 в БД (REG-005); автоматизацию БД пока отложили.
- Конкурентную регистрацию (CONC-001) выполнить позже.
- При необходимости дополнить заголовок для 201 и проверки БД; сравнение ID регистрации и профиля уже проверено.
- Пока не автоматизированы: комбинация регистра и пробелов в дубликате email (EMAIL-016), другой код страны (PHONE-006), полноширинные цифры (PHONE-015), тело другого типа (BODY-008), точное количество записей в БД (DATA-003).

<a id="registration-checklist-дополнительные-выполненные-сценарии"></a>

### Дополнительные выполненные сценарии

- [test_registered_password_is_case_sensitive](../tests/test_auth_flow.py): исходный пароль позволяет войти, изменение регистра первой буквы даёт 401 INVALID_CREDENTIALS.
- [test_rejected_registration_does_not_reserve_email](../tests/test_auth_flow.py): после 422 вход невозможен, исправленная регистрация с тем же email успешна. Это проверка через API, без SQL.

<a id="login-checklist"></a>

## Чек-лист входа пользователя

**Версия приложения:** для исторического этапа не зафиксирована; данные последнего стенда — в [журнале](test-runs.md).

Основание: [FR-01 и FR-02](requirements.md), [контракт API](api-specification.md) и схема Login из OpenAPI. Login принимает только email и password. Для пароля схема задаёт длину 10–128 символов; для email — корректный формат и максимум 254 символа.

Примеры данных в таблицах обозначают варианты проверки. В коде используются уникальные email. Каждый вариант параметризации запускается отдельно; количество строк чек-листа не равно количеству запусков тестов.

<a id="login-checklist-1-основные-сценарии"></a>

### 1. Основные сценарии

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-001 | Успешный вход | Активный зарегистрированный пользователь; верные email и пароль | `200`; access_token — непустая строка, token_type = bearer, expires_in = 3600 | Passed | [test_login_with_valid_credentials](../tests/test_login.py) |
| LOGIN-002 | Неверный пароль | Существующий email; другой пароль допустимой длины | `401`, error.code = INVALID_CREDENTIALS | Passed | [test_login_with_invalid_password](../tests/test_login.py) |
| LOGIN-003 | Несуществующий email | Уникальный валидный email без регистрации | `401`, error.code = INVALID_CREDENTIALS | Passed | [test_login_with_nonexistent_email](../tests/test_login.py) |
| LOGIN-004 | Вход отключённого пользователя | Создать пользователя и отключить через admin API; передать правильный пароль | `401`, error.code = INVALID_CREDENTIALS; access_token отсутствует | Passed | [test_login_with_disabled_user](../tests/test_login.py) |

Пользователя для LOGIN-004 создаёт фикстура disabled_user_credentials. Для подготовки доступа администратора используется локальная seed-учётная запись из [документации](README.md); готовый disabled@example.com не используется.

<a id="login-checklist-2-email-и-пароль"></a>

### 2. Email и пароль

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-005 | Верхний регистр email | Изменить регистр email существующего пользователя | `200`; непустой access_token | Passed | [test_login_normalizes_email](../tests/test_login.py) [uppercase] |
| LOGIN-006 | Крайние пробелы email | Окружить существующий email пробелами | `200`; непустой access_token | Passed | [test_login_normalizes_email](../tests/test_login.py) [spaces] |
| LOGIN-007 | Регистр и пробелы вместе | Верхний регистр email и пробелы по краям | `200`; непустой access_token | Passed | [test_login_normalizes_email](../tests/test_login.py) [both] |
| LOGIN-008 | Email не передан | Удалить email из тела | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_without_required_field](../tests/test_login.py) [email] |
| LOGIN-009 | Пароль не передан | Удалить password из тела | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_without_required_field](../tests/test_login.py) [password] |
| LOGIN-010 | Null в обязательных полях | По отдельности email = null и password = null | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_null_required_field](../tests/test_login.py) |
| LOGIN-011 | Неверные типы полей | Для каждого поля отдельно: целое число, дробное число, true, false, массив, объект | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_field_type](../tests/test_login.py) |
| LOGIN-012 | Пустой email и только пробелы | По отдельности пустая строка и строка из пробелов | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_email](../tests/test_login.py) [empty, spaces] |
| LOGIN-013 | Неверный формат email | userexample.com, user@, @example.com | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_email](../tests/test_login.py) |
| LOGIN-014 | Пустой пароль | password = пустая строка | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_empty_password](../tests/test_login.py) |
| LOGIN-015 | Регистр пароля значим | Войти с точным паролем, затем изменить регистр первой буквы | Исходный пароль — `200`; изменённый — `401 INVALID_CREDENTIALS` | Passed | [test_registered_password_is_case_sensitive](../tests/test_auth_flow.py); сквозной сценарий |
| LOGIN-016 | Крайние пробелы пароля запрещены | Допустимый пароль с пробелом перед/после | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py) |
| LOGIN-017 | Внутренний пробел пароля запрещён | `password 12345` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py) |
| LOGIN-018 | Кириллический пароль запрещён | `ПарольДляТеста` | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py) |
| LOGIN-019 | Границы длины пароля при входе | 9, 10, 128, 129 букв a; для допустимых значений зарегистрировать пользователя | 9 и 129 — `422`; 10 и 128 — `200` | Passed | [test_login_with_invalid_password_length](../tests/test_login.py); [test_register_and_login_with_allowed_ascii_password](../tests/test_auth_flow.py) |
| LOGIN-020 | Границы длины email при входе | Зарегистрированный адрес длиной 254, включая крайние пробелы; адрес длиной 255 | 254 после обрезки — `200`; 255 — `422`, поле `body.email` | Passed | [test_register_and_login_with_max_email_length](../tests/test_auth_flow.py); [test_login_with_email_exceeding_max_length](../tests/test_login.py) |
| LOGIN-021 | Email вне ASCII запрещён | Кириллица в обеих частях, иероглифы, emoji | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_login_with_invalid_email_characters](../tests/test_login.py) |
| LOGIN-022 | Пароль только из пробелов запрещён | 10 обычных пробелов | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py); only_spaces |
| LOGIN-035 | Иероглифы и emoji в пароле запрещены | Существующий пользователь; пароль с символами вне ASCII | `422 VALIDATION_ERROR`, поле `body.password`; токен не выдаётся | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py) |
| LOGIN-036 | Управляющие и невидимые символы пароля запрещены | Tab, LF, CR, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.password` | Passed | [test_login_with_invalid_password_characters](../tests/test_login.py) |
| LOGIN-037 | Недопустимые пробелы и управляющие символы email | Внутренний пробел, Tab, LF, NBSP, zero-width space, NUL, DEL | `422 VALIDATION_ERROR`, поле `body.email` | Passed | [test_login_with_invalid_email_characters](../tests/test_login.py) |
| LOGIN-038 | Пароль не требует сочетания категорий символов | Только буквы, цифры или пунктуация; полный набор печатных ASCII | С зарегистрированным паролем login `200` | Passed | [test_register_and_login_with_allowed_ascii_password](../tests/test_auth_flow.py) |


<a id="login-checklist-3-тело-запроса"></a>

### 3. Тело запроса

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-023 | Лишние поля | По одному добавить name, phone, role, is_active, password_hash, unexpected | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_extra_field](../tests/test_login.py) |
| LOGIN-024 | Отсутствующее тело | POST без содержимого тела, Content-Type: application/json | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py) [no_body] |
| LOGIN-025 | Пустой объект | Отправить {} | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py) [empty_object] |
| LOGIN-026 | Сломанный JSON | Незавершённый объект | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py) [malformed_json] |
| LOGIN-027 | Тело другого типа | null, массив, строка, число, boolean | `422`, error.code = VALIDATION_ERROR | Passed | [test_login_with_invalid_body](../tests/test_login.py) |

<a id="login-checklist-4-ошибки-и-отсутствие-секретов"></a>

### 4. Ошибки и отсутствие секретов

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| LOGIN-028 | Структура ошибки неверных учётных данных | Существующий пользователь; неверный пароль | `401 INVALID_CREDENTIALS`; тело соответствует ERROR_SCHEMA | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py) |
| LOGIN-029 | Структура ошибки валидации | Короткий пароль Q7!x | `422 VALIDATION_ERROR`; тело соответствует ERROR_SCHEMA; details указывает body.password | Passed | [test_login_validation_error_response](../tests/test_login.py) |
| LOGIN-030 | Идентификатор запроса в ошибках | Ответы 401 и 422 | Есть X-Request-ID, совпадает с error.request_id | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py); [test_login_validation_error_response](../tests/test_login.py) |
| LOGIN-031 | Заголовок авторизации при отказе | Неверный пароль | `401`; WWW-Authenticate = Bearer | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py) |
| LOGIN-032 | Пароли и токен не раскрываются в ошибке входа | Получить токен; затем выполнить неуспешный вход с паролем-маркером | `401`; в теле нет исходного и переданного паролей, ранее выданного токена, access_token и password_hash | Passed | [test_login_invalid_credentials_error_response](../tests/test_login.py) |
| LOGIN-033 | Секреты отсутствуют в ошибке валидации | Передать короткий пароль-маркер | `422`; в теле нет переданного пароля, access_token и password_hash | Passed | [test_login_validation_error_response](../tests/test_login.py) |
| LOGIN-034 | Идентификатор успешного запроса | Успешный login | `200`; есть X-Request-ID | Not run | В текущем успешном тесте заголовок не проверяется |

ERROR_SCHEMA хранится в [schemas/error_response.py](../schemas/error_response.py) и импортируется обычным Python-импортом. Схема проверяет структуру; статусы, коды ошибок и значения проверяются assert внутри тестов.

<a id="login-checklist-5-сквозные-сценарии-доступа"></a>

### 5. Сквозные сценарии доступа

Эти пункты используют несколько операций и находятся в test_auth_flow.py.

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| AUTH-001 | Выданный токен открывает профиль | Зарегистрироваться, войти, вызвать GET /users/me с токеном | Login `200`; профиль `200`, данные соответствуют пользователю | Passed | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py) |
| AUTH-002 | Деактивация закрывает доступ со старым токеном | Получить токен, убедиться в доступе, отключить пользователя, повторить GET /users/me | До отключения `200`; после — `401 UNAUTHORIZED` с тем же токеном | Passed | [test_disabled_user_cannot_use_existing_token](../tests/test_auth_flow.py) |
| AUTH-003 | Реактивация восстанавливает доступ | Получить токен, отключить пользователя, проверить отказ, включить обратно | Старый ещё не истёкший токен снова открывает профиль; новый login с исходным паролем успешен | Passed | [test_reactivated_user_can_use_existing_token_and_login](../tests/test_auth_flow.py) |

<a id="login-checklist-что-оставили-на-следующий-этап"></a>

### Что оставили на следующий этап

- LOGIN-034: заголовок X-Request-ID успешного входа пока не проверяется. Границы полей login уже покрыты.
- Проверки изменения email профиля реализованы: [чек-лист профиля](testing-auth.md#profile-checklist).
- Отсутствующий, пустой, сломанный JWT и повреждённая подпись проверены на трёх операциях в [общем блоке авторизации](#authorization). Истёкший JWT и неверные iss/aud отложены по решению владельца: для независимой проверки нужны корректно подписанные токены с изменёнными claims. Выдача непустой строки access_token и значение expires_in = 3600 сами по себе не подтверждают корректность содержимого и проверок JWT.

<a id="profile-checklist"></a>

## Чек-лист изменения профиля

Операция: `PATCH /api/v1/users/me`. Окружение: отдельный локальный стенд. Дата: 03.11.2026.

Основания: [FR-01 и FR-02](requirements.md#fr-01-пользователи-и-авторизация), [контракт API](api-specification.md#авторизация-и-профиль). Поля изменения — email, name, phone; хотя бы одно обязательно. `null` разрешён только для телефона. Правила ASCII относятся к email; кириллица в имени допустима.

| ID | Проверка | Ожидаемый результат | Статус | Автотест |
|---|---|---|---|---|
| PRF-001 | Изменить все поля, включая plus-tag и ASCII Punycode-домен | 200; нормализация; GET подтверждает сохранение; ID, роль и активность сохранены; вход работает с новым email, старый даёт 401 | Passed | [test_update_profile_all_fields](../tests/test_profile.py) |
| PRF-002 | Отдельно изменить имя или телефон, проверить границы | 200; имя обрезается до проверки длины; имя 1/100 символов и телефон 7/15 цифр с/без + допустимы; пропущенные поля сохранены | Passed | [test_update_profile_single_field](../tests/test_profile.py) |
| PRF-003 | Изменить только имя после установки email и телефона | 200; ранее сохранённые email и телефон не сбрасываются | Passed | [test_update_profile_preserves_omitted_fields](../tests/test_profile.py) |
| PRF-004 | Очистить ранее установленный телефон через null | 200; телефон null в PATCH и GET; остальные данные сохранены | Passed | [test_update_profile_can_clear_phone](../tests/test_profile.py) |
| PRF-005 | Email 254 символа, с крайними обычными пробелами и без них | 200; длина считается после обрезки; GET подтверждает нормализованный адрес | Passed | [test_update_profile_with_max_email_length](../tests/test_profile.py) |
| PRF-006 | Передать собственный email в исходном виде, верхнем регистре, с пробелами и их сочетанием | 200; email нормализован; конфликта с собой нет | Passed | [test_update_profile_with_own_email](../tests/test_profile.py) |
| PRF-007 | Email другого пользователя, включая варианты нормализации; одновременно валидные имя и телефон | 409 EMAIL_EXISTS; ошибка соответствует ERROR_SCHEMA; GET показывает исходный профиль без частичных изменений | Passed | [test_update_profile_rejects_existing_email](../tests/test_profile.py) |
| PRF-008 | Общая матрица недопустимых символов email | 422 VALIDATION_ERROR, body.email; валидное имя из того же запроса не сохраняется | Passed | [test_update_profile_rejects_invalid_email_characters](../tests/test_profile.py) |
| PRF-009 | Null имени/email; неверные формат и длина email, имени, телефона | 422 VALIDATION_ERROR; профиль не меняется; путь поля проверяется там, где это полевая ошибка | Passed | [test_update_profile_rejects_invalid_values](../tests/test_profile.py) |
| PRF-010 | Числа, boolean, массивы и объекты для каждого поля | 422 VALIDATION_ERROR с путём поля; профиль не меняется | Passed | [test_update_profile_rejects_invalid_types](../tests/test_profile.py) |
| PRF-011 | Передать роль, активность, пароль, хеш, ID, user_id, timestamps или неизвестное поле | 422 VALIDATION_ERROR; валидное изменение имени из того же запроса также не сохраняется | Passed | [test_update_profile_rejects_forbidden_fields](../tests/test_profile.py) |
| PRF-012 | Нет тела, пустой объект, сломанный JSON или тело другого типа | 422 VALIDATION_ERROR в едином формате; профиль не меняется | Passed | [test_update_profile_rejects_invalid_body](../tests/test_profile.py) |
| PRF-013 | Email 255 символов, с крайними пробелами и без них | 422 VALIDATION_ERROR, body.email; профиль не меняется | Passed | [test_update_profile_rejects_email_exceeding_max_length](../tests/test_profile.py) |
| PRF-014 | Нет Authorization, пустой Bearer или некорректный токен | 401 UNAUTHORIZED; WWW-Authenticate: Bearer; профиль не меняется | Passed | [test_update_profile_requires_authorization](../tests/test_profile.py) |
| PRF-015 | Отключить пользователя после выдачи токена, затем изменить профиль | 401 UNAUTHORIZED со старым токеном | Passed | [test_disabled_user_cannot_update_profile](../tests/test_profile.py) |
| PRF-016 | Изменить профиль, когда в стенде есть второй пользователь | Меняется только текущий пользователь; профиль второго остаётся прежним | Passed | [test_update_profile_changes_only_current_user](../tests/test_profile.py) |
| PRF-017 | Ошибка с паролем-маркером в запрещённом поле | 422; ERROR_SCHEMA; X-Request-ID совпадает с error.request_id; пароль и токен не отражаются; профиль не меняется | Passed | [test_update_profile_validation_error_response](../tests/test_profile.py) |

<a id="profile-checklist-известные-ограничения"></a>

### Известные ограничения

- В живой OpenAPI-схеме email и name допускают null через anyOf, но runtime-валидация и нормативные требования запрещают явный null. Это несоответствие схемы приложения; тесты не ослабляют контракт ради него. Для null имени проверяется отказ и отсутствие изменений без привязки к недокументированному пути модельной ошибки.
- Сохранность данных проверяется через GET API, без SQL. Хеш пароля и отсутствие прямых изменений в БД отдельно не проверяются.
- Истёкший JWT, неверные подпись/iss/aud, конкурентные PATCH, изменение профиля администратором и полная валидация ID/timestamps успешного ответа пока не покрыты этим модулем.
- Сведения о проверенном стенде — в [журнале](test-runs.md). Тесты не используют общие seed-профили и не сбрасывают БД.

<a id="registration-requirements-questions"></a>

## Решения и открытые вопросы к требованиям регистрации

| ID | Вопрос | Решение / статус |
|---|---|---|
| Q-REG-01 | Поддерживается ли кириллица в email до/после @? | Решено: обе части адреса должны быть ASCII. Кириллица, иероглифы, emoji и другие символы вне ASCII запрещены. |
| Q-REG-02 | Какие символы разрешены в пароле? | Решено: только печатные ASCII `U+0021–U+007E` без пробела, длина 10–128; обязательного сочетания категорий символов нет. |
| Q-REG-03 | Когда проверяется максимум email 254 символа? | Решено: после удаления крайних обычных пробелов ASCII `U+0020`. |
| Q-REG-04 | Разрешён ли пароль только из пробелов? | Решено: нет. Любые пробельные символы в любом месте пароля запрещены; пароль не обрезается. |
| Q-REG-05 | Разрешены ли в имени цифры, дефисы, апострофы и emoji? | Открыто: для имени пока определены длина 1–100 и удаление крайних пробелов. Ограничения email и пароля на имя не распространяются. |

Проверки регистрации и входа должны подтверждать отказ для кириллического пароля и пароля с пробелами. Проверки изменения email профиля реализованы: [чек-лист профиля](testing-auth.md#profile-checklist). Наблюдаемое поведение само по себе не заменяет требование.

<a id="authorization"></a>

## Общие проверки авторизации

Модуль: [test_authorization.py](../tests/test_authorization.py). Проверяется общий отказ в доступе на трёх операциях: GET `/users/me`, GET `/bookings`, POST `/hotels`. Последняя получает валидное тело создания, чтобы не смешивать ошибки авторизации и валидации. Каждый случай создаёт своего обычного пользователя.

| ID | Проверка | Ожидаемый результат | Статус |
|---|---|---|---|
| JWT-001 | Нет заголовка Authorization | 401 UNAUTHORIZED, ERROR_SCHEMA, совпадающий request ID, WWW-Authenticate: Bearer | Passed |
| JWT-002 | Пустой Bearer | Те же проверки отказа | Passed |
| JWT-003 | Некорректный формат JWT | Те же проверки отказа; токен не отражается в теле | Passed |
| JWT-004 | У настоящего токена изменён первый байт подписи, header и payload сохранены | Те же проверки отказа; токен остаётся синтаксически трёхчастным JWT с base64url-подписью | Passed |
| JWT-005 | Корректно подписанный, но истёкший JWT | По контракту 401 UNAUTHORIZED | Not run — отложено владельцем |
| JWT-006 | Корректно подписанный JWT с неверным iss/aud | По контракту 401 UNAUTHORIZED | Not run — отложено владельцем |

JWT-001–004 параметризованы по трём операциям: всего **12 случаев**, подтверждены отдельным прогоном. После каждого отказа исходный действующий токен по-прежнему открывает профиль. Ключ подписи не читается и не используется; дополнительных зависимостей нет. Изменённая подпись не является проверкой exp/iss/aud: сервер может отказать до обработки этих полей. Эти проверки не заменяют полную матрицу всех защищённых операций и не доказывают отсутствие записи отеля прямым подсчётом БД.

<a id="admin-operations-access"></a>

## Запрет административных операций обычному пользователю

Основание: [контракт API](api-specification.md). Модуль: [test_admin_operations_access.py](../tests/test_admin_operations_access.py). Используется действующий JWT активного пользователя; отдельная локальная фикстура проверяет его фактическую роль `user` через GET профиля. Ресурсы существуют, тела валидны, бронирований, мешающих архивированию, нет: проверяется именно право на операцию.

| ID | Операция / попытка | Ожидаемый результат | Статус |
|---|---|---|---|
| ADM-001 | POST /hotels | 403 FORBIDDEN; в уникальном городе не появляется отель | Passed |
| ADM-002 | PUT /hotels/{id} | 403; отель и его номер неизменны | Passed |
| ADM-003 | DELETE /hotels/{id} | 403; отель и номер остаются неархивными, доступны для чтения | Passed |
| ADM-004 | POST /hotels/{id}/rooms | 403; список номеров и total неизменны | Passed |
| ADM-005 | PUT /rooms/{id} | 403; цена и остальные данные номера неизменны | Passed |
| ADM-006 | PATCH /rooms/{id}/availability | 403; номер остаётся включённым | Passed |
| ADM-007 | DELETE /rooms/{id} | 403; номер неизменен и доступен для чтения | Passed |
| ADM-008 | GET /admin/users | 403; email текущего пользователя не отражается; контрольный admin-запрос успешен | Passed |
| ADM-009 | GET /admin/users/{id}, цель — сам пользователь или другой user | 403 в обоих случаях; admin успешно читает существующий ID | Passed |
| ADM-010 | PATCH /admin/users/{id}, цель self/other, изменение role=admin или is_active=false | 403 в четырёх случаях; admin перечитывает неизменённые данные, токен цели сохраняет доступ и роль user | Passed |

Всего **14 новых случаев для 10 операций**. Во всех отказах проверяются ERROR_SCHEMA, код FORBIDDEN и совпадение request ID. Сохранность проверяется через GET API; запрет создания — через контролируемую выборку. SQL-подсчёт и конкуренция не проверяются.

Новый блок вместе с общей авторизацией и целостностью бронирований: **32 passed за 17.13 с**, 03.11.2026. Полный набор после этих изменений не запускался по выбранной стратегии проверки только новых и связанных тестов. Отсутствующий/повреждённый JWT на всех этих операциях, позитивная матрица администрирования, валидация тел и защита последнего admin остаются отдельными задачами.
