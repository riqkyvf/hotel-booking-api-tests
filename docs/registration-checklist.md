# Чек-лист регистрации пользователя

**Операция:** `POST /api/v1/auth/register`  
**Окружение:** локальное API, `http://localhost:8000`  
**Дата составления:** 01.11.2026  
**Версия приложения / commit:** не зафиксирована  
**Дата ручного прогона:** не зафиксирована  
**Последний полный автопрогон:** 01.11.2026 — 145 passed по всему проекту

## Основания и статусы

- [FR-01 — пользователи и авторизация](requirements.md#fr-01-пользователи-и-авторизация).
- [Контракт API](api-specification.md): регистрация, формат ответа, ошибки и неизвестные поля.
- [Схема БД — users](database-schema.md#users).
- Живая OpenAPI-схема: `http://localhost:8000/openapi.json`, просмотрена 01.11.2026.

Статусы обновлены по полному автопрогону 01.11.2026. Колонка «Автотест / покрытие» связывает пункт с тестом и указывает ограничения. Колонка подтверждений не используется.

Из 94 пунктов чек-листа: 64 покрыты полностью, 14 частично, 10 не выполнялись в текущем автопрогоне, 6 требуют уточнения требований. Это оценка покрытия тестами, а не процент готовности продукта.

- `Passed` — пункт покрыт прошедшими автотестами.
- `Partial` — прошла только часть проверки; оставшаяся часть указана в колонке покрытия.
- `Not run` — соответствующего автотеста нет; в этом прогоне пункт не выполнялся.
- `Требует уточнения` — ожидаемое поведение ещё не согласовано.
- `Failed` / `Blocked` — расхождение с ожиданием / препятствие выполнению; в текущем прогоне таких результатов нет.

Ранее отмеченные пользователем ручные результаты не являются результатами текущего автопрогона. В частности, кириллица до и после @ принималась вручную, но её поддержка в email ещё требует согласования: [вопросы к требованиям](registration-requirements-questions.md).

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
| REG-011 | Вход после регистрации | Вызвать `/auth/login` с зарегистрированными email и паролем | `200`; выдан токен | Passed | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py#L7) |
| REG-012 | Чтение созданного профиля | С токеном из REG-011 вызвать `GET /users/me` | `200`; ID совпадает с регистрацией; профиль содержит сохранённые нормализованные значения | Partial | [test_registered_user_can_login_and_get_profile](../tests/test_auth_flow.py#L7); Профиль и вход проверены; сравнения ID с ответом регистрации нет |

## 2. Поле email

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| EMAIL-001 | Валидный email | Новый `qa.email.001@example.com` | `201`; email сохранён | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| EMAIL-002 | Приведение к нижнему регистру | Новый `QA.Email.002@EXAMPLE.COM` | `201`; в ответе и БД `qa.email.002@example.com` | Partial | [test_register_lowercases_email](../tests/test_registration.py#L151); Проверен ответ API; БД не проверяется |
| EMAIL-003 | Обрезка крайних пробелов | `"  qa.email.003@example.com  "` | `201`; в ответе и БД нет крайних пробелов | Partial | [test_register_trims_email](../tests/test_registration.py#L141); Проверен ответ API; БД не проверяется |
| EMAIL-004 | Дубликат email | Сначала создать пользователя, затем повторить его email | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py#L45) |
| EMAIL-005 | Обязательность поля | Удалить ключ `email` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py#L58) |
| EMAIL-006 | Пустая строка | `"email": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_email](../tests/test_registration.py#L166) |
| EMAIL-007 | Максимальная длина | Корректный по формату email длиной 254 символа | `201` | Passed | [test_register_with_max_email_length](../tests/test_registration.py#L210) |
| EMAIL-008 | Дубликат в другом регистре | Существующий email передать в другом регистре | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py#L45) |
| EMAIL-009 | Дубликат с крайними пробелами | Существующий email окружить пробелами | `409`, `error.code = EMAIL_EXISTS` | Passed | [test_register_with_existing_email](../tests/test_registration.py#L45) |
| EMAIL-010 | Превышение максимальной длины | Email длиной 255 символов, без иных нарушений формата, насколько это возможно | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_email_exceeding_max_length](../tests/test_registration.py#L221) |
| EMAIL-011 | Неверный формат | По отдельности: `userexample.com`, `user@`, `@example.com` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_email](../tests/test_registration.py#L166) |
| EMAIL-012 | Неверный тип | Число / boolean; исходный набор значений уточнить | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L196) |
| EMAIL-013 | Явный null | `"email": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py#L176) |
| EMAIL-014 | Только пробелы | `"email": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_email](../tests/test_registration.py#L166) |
| EMAIL-015 | Массив и объект | По отдельности: `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L196) |
| EMAIL-016 | Комбинация нормализации при дубликате | Существующий email одновременно в другом регистре и с пробелами по краям | `409`, `error.code = EMAIL_EXISTS` | Not run | Не автоматизировано |
| EMAIL-017 | Кириллица до @ принимается | Например, `пользователь@example.com`; точный адрес прошлого прогона не зафиксирован | Регистрация успешна (`201`); приём кириллицы подтверждён пользователем, нормативное правило уточняется в Q-REG-01 | Требует уточнения | Автотеста нет; Q-REG-01. Для EMAIL-017 и EMAIL-018 ранее сообщалось об успешном ручном приёме |
| EMAIL-018 | Кириллица после @ принимается | Например, `qa.reg.018@пример.рф`; точный адрес прошлого прогона не зафиксирован | Регистрация успешна (`201`); приём кириллицы подтверждён пользователем, нормативное правило уточняется в Q-REG-01 | Требует уточнения | Автотеста нет; Q-REG-01. Для EMAIL-017 и EMAIL-018 ранее сообщалось об успешном ручном приёме |
| EMAIL-019 | Кириллица одновременно до и после @ | Новый `пользователь019@пример.рф` | Рабочее ожидание: `201`; подтвердить по Q-REG-01 | Требует уточнения | Автотеста нет; Q-REG-01. Для EMAIL-017 и EMAIL-018 ранее сообщалось об успешном ручном приёме |
| EMAIL-020 | Нормализация кириллического email | Новый `"  ПОЛЬЗОВАТЕЛЬ020@ПРИМЕР.РФ  "`; проверить ответ и БД | Рабочее ожидание: `201`; крайние пробелы удалены, email приведён к нижнему регистру | Требует уточнения | Автотеста нет; Q-REG-01. Для EMAIL-017 и EMAIL-018 ранее сообщалось об успешном ручном приёме |
| EMAIL-021 | Дубликат кириллического email после нормализации | Создать `пользователь021@пример.рф`; повторить как `"  ПОЛЬЗОВАТЕЛЬ021@ПРИМЕР.РФ  "` | При поддержке этих адресов — `409`, `error.code = EMAIL_EXISTS`; одна запись в БД | Требует уточнения | Автотеста нет; Q-REG-01. Для EMAIL-017 и EMAIL-018 ранее сообщалось об успешном ручном приёме |
| EMAIL-022 | Вход и чтение профиля с кириллическим email | Отдельно для EMAIL-017 и EMAIL-018: зарегистрировать нового пользователя, выполнить login с исходным email, затем GET `/users/me` | Рабочее ожидание: регистрация `201`, login `200`, профиль `200`; ID совпадает с регистрацией, email соответствует сохранённому значению | Требует уточнения | Автотеста нет; Q-REG-01. Для EMAIL-017 и EMAIL-018 ранее сообщалось об успешном ручном приёме |

Пример подготовки длинного адреса: 64 символа `a`, затем `@`, затем домен из меток длиной 63, 63 и 61, разделённых точками — всего 254 символа. Для 255 увеличить последнюю метку до 62. В протоколе прогона сохранить получившиеся строки. Проверять, что причина отказа относится к исследуемому ограничению, а не к другому правилу email.

## 3. Поле password

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| PASS-001 | Валидный пароль | `HotelDemo123!` | `201` | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| PASS-002 | Значимость пробелов | Исходные данные ручной проверки не зафиксированы | Крайние и внутренние пробелы не удаляются из пароля | Passed | [test_register_preserves_password_spaces](../tests/test_auth_flow.py#L46) |
| PASS-003 | Пароль короче минимума | Строка длиной менее 10; исходная длина не зафиксирована | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L74) |
| PASS-004 | Пароль длиннее максимума | Строка длиной более 128; исходная длина не зафиксирована | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L74) |
| PASS-005 | Обязательность поля | Удалить ключ `password` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py#L58) |
| PASS-006 | Неверный тип | Число / boolean; исходный набор значений уточнить | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L196) |
| PASS-007 | Точные границы | По отдельности: 9, 10, 128, 129 символов | Соответственно `422`, `error.code = VALIDATION_ERROR` / `201` / `201` / `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L74); Также test_register_with_valid_password_length: вместе проверены 9, 10, 128 и 129 |
| PASS-008 | Пустая строка | `"password": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_password_length](../tests/test_registration.py#L74) |
| PASS-009 | Явный null | `"password": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py#L176) |
| PASS-010 | Массив и объект | По отдельности: `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L196) |
| PASS-011 | Крайние пробелы сохраняются при регистрации | Зарегистрировать с `" Abcdef1234 "`; выполнить login с точным паролем и отдельно с `"Abcdef1234"` | Регистрация `201`; точный пароль — login `200`; обрезанный — `401 INVALID_CREDENTIALS` | Passed | [test_register_preserves_password_spaces](../tests/test_auth_flow.py#L46) |
| PASS-012 | Внутренний пробел значим | Зарегистрировать с `"Abcde 12345"`; выполнить login с исходным паролем и отдельно с `"Abcde12345"` | Регистрация `201`; исходный пароль — login `200`; без пробела — `401 INVALID_CREDENTIALS` | Passed | [test_register_preserves_password_spaces](../tests/test_auth_flow.py#L46) |
| PASS-013 | Пароль из кириллицы принимается | Например, `ПарольДляТеста`; точный пароль прошлого прогона не зафиксирован | `201`; приём кириллицы подтверждён пользователем | Passed | [test_register_and_login_with_cyrillic_password](../tests/test_auth_flow.py#L158) |
| PASS-014 | Вход с паролем из кириллицы | Зарегистрировать с `ПарольДляТеста`; выполнить login с точным паролем | Регистрация `201`; login `200` | Passed | [test_register_and_login_with_cyrillic_password](../tests/test_auth_flow.py#L158) |
| PASS-015 | Пароль со смешением кириллицы и латиницы | `ПарольTest123`; после регистрации выполнить login | Регистрация `201`; login с точным паролем `200` | Not run | Не автоматизировано |
| PASS-016 | Похожие кириллические и латинские буквы различаются | Зарегистрировать с `TestPassword123a` (последняя буква — латинская a); войти с `TestPassword123а` (последняя — кириллическая а), затем с исходным паролем | Регистрация `201`; пароль с заменённой буквой — `401 INVALID_CREDENTIALS`; исходный — `200` | Not run | Не автоматизировано |
| PASS-017 | Границы длины пароля из кириллицы | Отдельно 9, 10, 128, 129 повторений буквы `я`; для принятых паролей выполнить login | Регистрация: 9 и 129 — `422`, `error.code = VALIDATION_ERROR`; 10 и 128 — `201`; login с принятыми паролями — `200` | Not run | Не автоматизировано |


## 4. Поле name

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| NAME-001 | Валидное имя | `Test User` | `201`; имя сохранено | Passed | [test_register_without_phone](../tests/test_registration.py#L9) |
| NAME-002 | Обрезка крайних пробелов | `"  Test User  "` | `201`; в ответе и БД `Test User` | Partial | [test_register_trims_name](../tests/test_registration.py#L127); Проверен ответ API; БД не проверяется |
| NAME-003 | Пустое имя | `"name": ""` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py#L98) |
| NAME-004 | Имя пустое после обрезки | `"name": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py#L98) |
| NAME-005 | Минимальная допустимая длина | `"name": "A"` | `201` | Passed | [test_register_with_valid_name_length](../tests/test_registration.py#L109) |
| NAME-006 | Максимальная допустимая длина | 100 символов `a` | `201` | Passed | [test_register_with_valid_name_length](../tests/test_registration.py#L109) |
| NAME-007 | Превышение максимальной длины | 101 символ `a` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_name](../tests/test_registration.py#L98) |
| NAME-008 | Длина проверяется после обрезки | 100 символов `a`, окружённых двумя пробелами с каждой стороны | `201`; сохранены 100 символов без крайних пробелов | Passed | [test_register_trims_name](../tests/test_registration.py#L127) |
| NAME-009 | Обязательность поля | Удалить ключ `name` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_without_required_field](../tests/test_registration.py#L58) |
| NAME-010 | Неверные типы | По отдельности: `123`, `true`, `false`, `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L196) |
| NAME-011 | Явный null | `"name": null` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_null_required_field](../tests/test_registration.py#L176) |
| NAME-012 | Кириллица | `Евгений` | `201`; имя сохранено корректно | Passed | [test_register_with_cyrillic_name](../tests/test_registration.py#L376) |

## 5. Поле phone

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| PHONE-001 | Корректный телефон | `+79991234567` | `201`; значение сохранено | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L234); Используются граничные номера, а не точный пример строки чек-листа |
| PHONE-002 | Явный null | `"phone": null` | `201`; `phone = null` в ответе и БД | Partial | [test_register_with_null_phone](../tests/test_registration.py#L254); Проверен ответ API; БД не проверяется |
| PHONE-003 | Пустая строка | `"phone": ""` | `422`, `error.code = VALIDATION_ERROR` по OpenAPI; пустая строка не равна null | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L290) |
| PHONE-004 | Только пробелы | `"phone": "   "` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L290) |
| PHONE-005 | Телефон без плюса | `79991234567` как JSON-строка | `201`; значение соответствует переданному | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L234); Используются граничные номера, а не точный пример строки чек-листа |
| PHONE-006 | Другой начальный код | `+441234567890` | `201`; ограничения на код страны нет | Not run | Не автоматизировано |
| PHONE-007 | Меньше минимума | 6 цифр без плюса и отдельно с плюсом | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone_length](../tests/test_registration.py#L245) |
| PHONE-008 | Минимальная длина | 7 цифр без плюса и отдельно с плюсом | `201` | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L234) |
| PHONE-009 | Максимальная длина | 15 цифр без плюса и отдельно с плюсом | `201`; плюс не входит в количество цифр | Passed | [test_register_with_valid_phone_length](../tests/test_registration.py#L234) |
| PHONE-010 | Превышение максимума | 16 цифр без плюса и отдельно с плюсом | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone_length](../tests/test_registration.py#L245) |
| PHONE-011 | Неверные типы | По отдельности: `1234567890` как число, `true`, `false`, `[]`, `{}` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_field_type](../tests/test_registration.py#L196); Проверены типы и указание ошибочного поля; число при преобразовании в строку укладывается в допустимую длину телефона |
| PHONE-012 | Буквы | `+7999abc4567` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L290) |
| PHONE-013 | Дефисы, скобки, внутренние пробелы | По отдельности: `7999-1234567`, `(7999)1234567`, `7999 1234567` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L290) |
| PHONE-014 | Неверное положение или количество плюсов | По отдельности: `++79991234567`, `79991234567+` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L290) |
| PHONE-015 | Цифры вне ASCII | `１２３４５６７` — полноширинные цифры | `422`, `error.code = VALIDATION_ERROR`: шаблон допускает только `[0-9]` | Not run | Не автоматизировано |
| PHONE-016 | Кириллица в телефоне | `+7999абв4567` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_phone](../tests/test_registration.py#L290) |

Отсутствие телефона покрыто REG-001. Явный null проверяется отдельно в PHONE-002.

## 6. Тело запроса и защита серверных полей

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| BODY-001 | Назначение роли клиентом запрещено | Добавить к валидному телу `"role": "admin"` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py#L312); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-002 | Изменение активности клиентом запрещено | Добавить `"is_active": false` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py#L312); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-003 | Передача хеша запрещена | Добавить `"password_hash": "some-value"` | `422`, `error.code = VALIDATION_ERROR`; пользователь не создан | Partial | [test_register_with_extra_field](../tests/test_registration.py#L312); Проверен отказ; отсутствие записи после запроса не проверяется |
| BODY-004 | Произвольное неизвестное поле запрещено | Добавить `"unexpected": "value"` | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_extra_field](../tests/test_registration.py#L312) |
| BODY-005 | Передача серверных идентификатора и времени запрещена | По одному добавлять `id`, `created_at`, `updated_at` с корректными по формату значениями | `422`, `error.code = VALIDATION_ERROR` для каждого поля | Passed | [test_register_with_extra_field](../tests/test_registration.py#L312) |
| BODY-006 | Пустой JSON-объект | `{}` | `422`, `error.code = VALIDATION_ERROR`; указаны ошибки обязательных полей | Partial | [test_register_with_invalid_body](../tests/test_registration.py#L331); Проверены 422 и code; состав ошибок обязательных полей здесь не проверяется |
| BODY-007 | Отсутствие тела | Отправить POST без тела | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_body](../tests/test_registration.py#L331) |
| BODY-008 | Тело не является объектом | По отдельности: `null`, `[]`, `"text"`, `123`, `true` | `422`, `error.code = VALIDATION_ERROR` для каждого значения | Not run | Не автоматизировано |
| BODY-009 | Синтаксически неверный JSON | Например, отсутствует закрывающая фигурная скобка | `422`, `error.code = VALIDATION_ERROR` | Passed | [test_register_with_invalid_body](../tests/test_registration.py#L331) |

## 7. Ошибки, отсутствие побочных изменений и конкуренция

| ID | Проверка | Тестовые данные / действие | Ожидаемый результат | Статус | Автотест / покрытие |
|---|---|---|---|---|---|
| RESP-001 | Единый формат ошибки валидации | Передать короткий пароль `Q7!x` | `422`, `error.code = VALIDATION_ERROR`; объект `error` содержит `code`, `message`, `details`, `request_id`; элементы details содержат `field`, `message`, `type` | Passed | [test_register_validation_error_response](../tests/test_registration.py#L343) |
| RESP-002 | Единый формат конфликта email | Повторить регистрацию существующего email | `409`, `error.code = EMAIL_EXISTS`; присутствуют `error.message`, `details`, `request_id` | Passed | [test_register_duplicate_email_error_response](../tests/test_registration.py#L361) |
| RESP-003 | Идентификатор запроса | Проверить ответы `201`, `409`, `422` | В каждом есть серверный заголовок `X-Request-ID` | Partial | [test_register_validation_error_response](../tests/test_registration.py#L343); Также test_register_duplicate_email_error_response; заголовок проверен для 422 и 409, для 201 ещё нет |
| RESP-004 | Пароль не раскрывается в ошибках | Передать узнаваемый пароль-маркер; вызвать 422, затем отдельно 409 | Ответы не содержат переданный пароль, хеш или полное исходное тело с секретами | Passed | [test_register_validation_error_response](../tests/test_registration.py#L343); Также test_register_duplicate_email_error_response; проверены пароль-маркер и отсутствие password_hash, без чтения БД |
| DATA-001 | Отказ валидации не создаёт пользователя | Новый email; невалидное имя; сравнить БД до и после | `422`, `error.code = VALIDATION_ERROR`; запись с новым email отсутствует | Partial | [test_rejected_registration_does_not_reserve_email](../tests/test_auth_flow.py#L112); Проверены отказ входа и последующая регистрация того же email; отсутствие строки в БД напрямую не проверяется |
| DATA-002 | Конфликт не изменяет существующего пользователя | Существующий email; другие валидные name, phone и password | `409`, `error.code = EMAIL_EXISTS`; поля существующей записи и хеш не изменились; новых записей нет | Partial | [test_duplicate_registration_does_not_change_user](../tests/test_auth_flow.py#L72); Проверены имя, email и работа старого пароля; phone, хеш и количество записей в БД не проверяются |
| DATA-003 | Создаётся ровно один пользователь | Валидная регистрация; сравнить БД до и после | `201`; одна новая запись с ID из ответа | Not run | Не автоматизировано |
| CONC-001 | Одновременная регистрация одного email | Два параллельных валидных запроса с одинаковым новым email | Один `201`, другой `409`, `error.code = EMAIL_EXISTS`; в БД одна запись; нет `500` | Not run | Не автоматизировано; конкурентный сценарий отложен |

## Уточнения перед следующим прогоном

- Вопросы о кириллице, длине email и допустимых символах вынесены в [вопросы к требованиям регистрации](registration-requirements-questions.md). Проверки с неопределённым ожиданием до согласования не оценивать как Passed/Failed.
- При следующем прогоне заполнить версию приложения и дату. Не сохранять в публичном портфолио действующие токены или реальные учётные данные.

## Что осталось

- Уточнить поддержку кириллицы в email (EMAIL-017–022).
- Вручную проверить Argon2 в БД (REG-005); автоматизацию БД пока отложили.
- Конкурентную регистрацию (CONC-001) выполнить позже.
- Дополнить частично покрытые пункты при необходимости: сравнение ID, заголовок для 201 и проверки БД.
- Пока не автоматизированы: комбинация регистра и пробелов в дубликате email (EMAIL-016), смешанный пароль и похожие буквы (PASS-015–016), кириллические границы (PASS-017), другой код страны (PHONE-006), полноширинные цифры (PHONE-015), тело другого типа (BODY-008), точное количество записей в БД (DATA-003).

## Дополнительные выполненные сценарии

- [test_registered_password_is_case_sensitive](../tests/test_auth_flow.py): исходный пароль позволяет войти, изменение регистра первой буквы даёт 401 INVALID_CREDENTIALS.
- [test_rejected_registration_does_not_reserve_email](../tests/test_auth_flow.py): после 422 вход невозможен, исправленная регистрация с тем же email успешна. Это проверка через API, без SQL.

Один пункт чек-листа может соответствовать нескольким запускам параметризованного теста, а один тест — нескольким пунктам. Поэтому 145 passed по проекту не означает 145 полностью закрытых пунктов этого чек-листа.
