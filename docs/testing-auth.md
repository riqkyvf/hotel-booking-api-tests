# Пользователи и авторизация

Контракт: [FR-01. Пользователи и авторизация](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-01-пользователи-и-авторизация), [FR-02. Деактивация](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-02-деактивация) и [REST-спецификация](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/api-specification.md#авторизация-и-профиль) коммита приложения из [CI](../.github/workflows/api-tests.yml).

**Разделы:** [регистрация](#registration-checklist) · [вход](#login-checklist) · [профиль](#profile-checklist) · [JWT и права](#authorization) · [администрирование](#admin-users).

[Как читать матрицы](README.md#check-catalog). Все разделы сопоставлены статически с требованиями и кодом; статусы не означают успешный прогон.

В тестах с [assert_api_error](../tests/assertions.py) проверяются схема ошибки, HTTP-статус, код и совпадение request ID в теле и заголовке.

<a id="registration-checklist"></a>

## Регистрация

Источники: FR-01, FR-10 и REST-спецификация. Общие условия: новый уникальный email, корректные остальные поля, запрос без авторизации. Варианты символов и допустимых паролей — в [data/auth.py](../data/auth.py).

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| REG-001 | <a id="reg-001"></a>Регистрация → `201`, переданные email/имя/телефон, роль `user`, активность true; пароль и хеш отсутствуют | Телефон не передан → `null`; передан корректный телефон | Высокая | Покрыто | [test_register_without_phone](../tests/auth/test_registration.py), [test_register_with_phone](../tests/auth/test_registration.py) |
| REG-002 | <a id="reg-002"></a>Дубликат нормализованного email → `409 EMAIL_EXISTS`, прежние имя и пароль сохраняются | Точный email; `email_variant=uppercase` / `spaces`; сохранность имени и пароля проверена для точного email | Высокая | Покрыто | [test_register_with_existing_email](../tests/auth/test_registration.py), [test_duplicate_registration_does_not_change_user](../tests/auth/test_auth_flow.py) |
| REG-003 | <a id="reg-003"></a>Клиент не назначает роль/активность и серверные поля → `422 VALIDATION_ERROR` соответствующего поля | По одному: `role=admin`, `is_active=false`, `password_hash`, `id`, `created_at`, `updated_at`, `unexpected` | Высокая | Покрыто | [test_register_with_extra_field](../tests/auth/test_registration.py) |
| REG-004 | <a id="reg-004"></a>Отказ в регистрации не резервирует email: вход невозможен, исправленный запрос → `201` | Пустое имя, затем исходные валидные данные с тем же email | Высокая | Покрыто | [test_rejected_registration_does_not_reserve_email](../tests/auth/test_auth_flow.py) |
| REG-005 | <a id="reg-005"></a>Допустимый ASCII-пароль не требует сочетания классов символов; регистрация → `201`, вход тем же паролем → `200` | `min_length_letters_only` (10), `max_length_letters_only` (128), `digits_only`, `punctuation_only` | Высокая | Покрыто | [test_register_and_login_with_allowed_ascii_password](../tests/auth/test_auth_flow.py) |
| REG-006 | <a id="reg-006"></a>Email обрезается по крайним U+0020 и приводится к нижнему регистру; ASCII и Punycode принимаются | `leading`, `trailing`, `both`; uppercase; `example.com`, Punycode-домен, `+tag`; вход тем же адресом с регистром и пробелами | Средняя | Покрыто | [test_register_trims_email](../tests/auth/test_registration.py), [test_register_lowercases_email](../tests/auth/test_registration.py), [test_register_and_login_with_ascii_email](../tests/auth/test_auth_flow.py) |
| REG-007 | <a id="reg-007"></a>Длина email после обрезки: 254 принимается → `201`, 255 отклоняется → `422 VALIDATION_ERROR` | `exact`, `with_outer_spaces` для 254; 255 без крайних пробелов | Средняя | Покрыто | [test_register_with_max_email_length](../tests/auth/test_registration.py), [test_register_with_email_exceeding_max_length](../tests/auth/test_registration.py) |
| REG-008 | <a id="reg-008"></a>Неверный формат или запрещённые символы email → `422 VALIDATION_ERROR` поля `body.email` | Без @/домена/локальной части, пустой/пробельный; `cyrillic_local`, `cyrillic_domain`, `internal_space`, `leading_tab`, `zero_width_space` | Средняя | Частично: display name, CJK/emoji, перенос строки и остальные управляющие символы отдельно не проверены | [test_register_with_invalid_email](../tests/auth/test_registration.py), [test_register_with_invalid_email_characters](../tests/auth/test_registration.py) |
| REG-009 | <a id="reg-009"></a>Невалидный пароль → `422 VALIDATION_ERROR` поля `body.password` | Длина 0/9/129; `trailing_space`, `internal_space`, `cyrillic`, `trailing_newline` | Средняя | Частично: CJK/emoji, табуляция и невидимые символы отдельно не проверены | [test_register_with_invalid_password_length](../tests/auth/test_registration.py), [test_register_with_invalid_password_characters](../tests/auth/test_registration.py) |
| REG-010 | <a id="reg-010"></a>Имя длиной 1–100 принимается; пустое, пробельное и 101 символ → `422 VALIDATION_ERROR` | Границы 1/100 → `201`; `empty`, `spaces`, `too_long` → `422` | Средняя | Покрыто | [test_register_with_valid_name_length](../tests/auth/test_registration.py), [test_register_with_invalid_name](../tests/auth/test_registration.py) |
| REG-011 | <a id="reg-011"></a>Крайние пробелы имени удаляются, кириллица сохраняется | `regular_name`, `min_length`, `max_length` после обрезки; кириллическое имя | Средняя | Покрыто | [test_register_trims_name](../tests/auth/test_registration.py), [test_register_with_cyrillic_name](../tests/auth/test_registration.py) |
| REG-012 | <a id="reg-012"></a>Необязательный телефон: `null` и 7–15 цифр с необязательным плюсом принимаются → `201` | Явный `null`; 7/15 цифр × `without_plus` / `with_plus` | Средняя | Покрыто | [test_register_with_null_phone](../tests/auth/test_registration.py), [test_register_with_valid_phone_length](../tests/auth/test_registration.py) |
| REG-013 | <a id="reg-013"></a>Неверные длина/формат телефона → `422 VALIDATION_ERROR` поля `body.phone` | 6/16 цифр ±плюс; пустой, пробелы, латинские/кириллические буквы, дефис, скобки, внутренний пробел, двойной/конечный/одинокий плюс | Средняя | Покрыто | [test_register_with_invalid_phone_length](../tests/auth/test_registration.py), [test_register_with_invalid_phone](../tests/auth/test_registration.py) |
| REG-014 | <a id="reg-014"></a>Обязательные поля нельзя пропускать или передавать `null` → `422 VALIDATION_ERROR` нужного поля | `email`, `password`, `name`: отсутствие / `null` | Средняя | Покрыто | [test_register_without_required_field](../tests/auth/test_registration.py), [test_register_with_null_required_field](../tests/auth/test_registration.py) |
| REG-015 | <a id="reg-015"></a>Поля регистрации не принимают нестроковые значения → `422 VALIDATION_ERROR` нужного поля | `email`, `password`, `name`, `phone` × integer, float, true, false, array, object | Средняя | Покрыто | [test_register_with_invalid_field_type](../tests/auth/test_registration.py) |
| REG-016 | <a id="reg-016"></a>Отсутствующее/сломанное JSON-тело и массив → `422 VALIDATION_ERROR` | `no_body`, `malformed_json`, `array` | Средняя | Покрыто | [test_register_with_invalid_body](../tests/auth/test_registration.py) |
| REG-017 | <a id="reg-017"></a>Ошибки регистрации соблюдают общий контракт и не раскрывают пароль/хеш | Короткий пароль → `422 VALIDATION_ERROR`; точный дубликат → `409 EMAIL_EXISTS`; схема, код, request ID | Средняя | Покрыто | [test_register_validation_error_response](../tests/auth/test_registration.py), [test_register_duplicate_email_error_response](../tests/auth/test_registration.py) |
| REG-018 | <a id="reg-018"></a>JSON `null` вместо объекта регистрации → `422 VALIDATION_ERROR` | Тело целиком `null`, а не `null` отдельного поля | Средняя | Не покрыто | — |

Границы пароля также проверяет [test_register_with_valid_password_length](../tests/auth/test_registration.py); вход с email длиной 254 — [test_register_and_login_with_max_email_length](../tests/auth/test_auth_flow.py). Хеширование Argon2 не доказывается этими HTTP-проверками.

<a id="login-checklist"></a>

## Вход

Источники: FR-01, FR-02, FR-10 и REST-спецификация. Корректный пользователь заранее зарегистрирован, кроме явно неизвестного email. Варианты символов используют те же наборы [data/auth.py](../data/auth.py).

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| LOG-001 | <a id="log-001"></a>Валидный вход → `200`, непустой строковый `access_token`, `token_type=bearer`, `expires_in=3600`; токен открывает собственный профиль | Активный пользователь, исходные данные; сквозной сценарий входит в `smoke` | Высокая | Покрыто | [test_login_with_valid_credentials](../tests/auth/test_login.py), [test_registered_user_can_login_and_get_profile](../tests/auth/test_auth_flow.py) |
| LOG-002 | <a id="log-002"></a>Валидные по формату, но неверные данные или деактивация → `401 INVALID_CREDENTIALS` | Неизвестный email; неверный пароль существующего пользователя; отключённый пользователь | Высокая | Покрыто | [test_login_with_nonexistent_email](../tests/auth/test_login.py), [test_login_invalid_credentials_error_response](../tests/auth/test_login.py), [test_login_with_disabled_user](../tests/auth/test_login.py) |
| LOG-003 | <a id="log-003"></a>Регистр пароля сохраняется и влияет на вход | Исходный пароль → `200`, изменён регистр первой буквы → `401 INVALID_CREDENTIALS` | Высокая | Покрыто | [test_registered_password_is_case_sensitive](../tests/auth/test_auth_flow.py) |
| LOG-004 | <a id="log-004"></a>Email нормализуется перед входом → `200`, непустой токен | `email_variant=uppercase` / `spaces` / `both` | Средняя | Покрыто | [test_login_normalizes_email](../tests/auth/test_login.py) |
| LOG-005 | <a id="log-005"></a>Обязательные поля нельзя пропускать или передавать `null` → `422 VALIDATION_ERROR` нужного поля | `email`, `password`: отсутствие / `null` | Средняя | Покрыто | [test_login_without_required_field](../tests/auth/test_login.py), [test_login_with_null_required_field](../tests/auth/test_login.py) |
| LOG-006 | <a id="log-006"></a>Поля входа не принимают нестроковые значения → `422 VALIDATION_ERROR` | `email`, `password` × integer, float, true, false, array, object | Средняя | Покрыто | [test_login_with_invalid_field_type](../tests/auth/test_login.py) |
| LOG-007 | <a id="log-007"></a>Лишние поля входа → `422 VALIDATION_ERROR` нужного поля | По одному: `name`, `phone`, `role`, `is_active`, `password_hash`, `unexpected` | Средняя | Покрыто | [test_login_with_extra_field](../tests/auth/test_login.py) |
| LOG-008 | <a id="log-008"></a>Невалидный формат/символы email отклоняются валидацией → `422`, а не проверкой учётных данных | Без @/домена/локальной части, пустой/пробельный; пять вариантов `INVALID_EMAIL_CHARACTER_CASES`; код `VALIDATION_ERROR` | Средняя | Частично: display name, CJK/emoji, перенос строки и остальные управляющие символы отдельно не проверены | [test_login_with_invalid_email](../tests/auth/test_login.py), [test_login_with_invalid_email_characters](../tests/auth/test_login.py) |
| LOG-009 | <a id="log-009"></a>Email длиной 255 после обрезки → `422 VALIDATION_ERROR` поля `body.email` | `exact`, `with_outer_spaces` | Средняя | Покрыто | [test_login_with_email_exceeding_max_length](../tests/auth/test_login.py) |
| LOG-010 | <a id="log-010"></a>Невалидный пароль отклоняется валидацией → `422 VALIDATION_ERROR` поля `body.password` | Длина 0/9/129; `trailing_space`, `internal_space`, `cyrillic`, `trailing_newline` | Средняя | Частично: CJK/emoji, табуляция и невидимые символы отдельно не проверены | [test_login_with_empty_password](../tests/auth/test_login.py), [test_login_with_invalid_password_length](../tests/auth/test_login.py), [test_login_with_invalid_password_characters](../tests/auth/test_login.py) |
| LOG-011 | <a id="log-011"></a>Отсутствующее/сломанное JSON-тело и массив → `422 VALIDATION_ERROR` | `no_body`, `malformed_json`, `array` | Средняя | Покрыто | [test_login_with_invalid_body](../tests/auth/test_login.py) |
| LOG-012 | <a id="log-012"></a>Ошибки входа соблюдают общий контракт, не раскрывают пароли, токен и хеш | Неверный пароль → `401`, `WWW-Authenticate: Bearer`; короткий пароль → `422`; схема, код, request ID | Средняя | Покрыто | [test_login_invalid_credentials_error_response](../tests/auth/test_login.py), [test_login_validation_error_response](../tests/auth/test_login.py) |
| LOG-013 | <a id="log-013"></a>JSON `null` вместо объекта входа → `422 VALIDATION_ERROR` | Тело целиком `null` | Средняя | Не покрыто | — |

Успешный вход с допустимыми классами/границами пароля и ASCII/Punycode-email — [REG-005](#reg-005), [REG-006](#reg-006); email длиной 254 — [test_register_and_login_with_max_email_length](../tests/auth/test_auth_flow.py). `expires_in=3600` в LOG-001 не доказывает фактическое истечение JWT через час; параметры и жизненный цикл токена относятся к разделу [JWT и права](#authorization).

<a id="profile-checklist"></a>

## Профиль

Источники: FR-01, FR-02, FR-10 и REST-спецификация. Общие условия: собственный активный пользователь и действующий JWT, кроме проверок отказа в доступе. Наборы значений — [data/profile.py](../data/profile.py) и [data/auth.py](../data/auth.py). Для успешных PATCH ниже результат повторно читается через GET; после отказов валидации и конфликта email профиль сравнивается с исходным.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| PRF-001 | <a id="prf-001"></a>GET возвращает собственный профиль → `200`, без пароля и хеша | ID, email, имя, `phone=null`, роль `user`, активность true; сценарий `smoke` | Высокая | Покрыто | [test_registered_user_can_login_and_get_profile](../tests/auth/test_auth_flow.py) |
| PRF-002 | <a id="prf-002"></a>PATCH всех изменяемых полей → `200`; email и имя нормализованы, серверные поля сохранены | Email с uppercase и крайними пробелами, `+tag`, ASCII/Punycode-домен; имя с крайними пробелами; телефон с плюсом; вход по новому email → `200`, по старому → `401 INVALID_CREDENTIALS`; прежний JWT работает | Высокая | Покрыто | [test_update_profile_all_fields](../tests/users/test_profile.py) |
| PRF-003 | <a id="prf-003"></a>Частичный PATCH сохраняет пропущенные поля | Отдельно имя или телефон; отдельно изменение имени после установки нового email и непустого телефона | Высокая | Покрыто | [test_update_profile_single_field](../tests/users/test_profile.py), [test_update_profile_preserves_omitted_fields](../tests/users/test_profile.py) |
| PRF-004 | <a id="prf-004"></a>Изменение затрагивает только текущего пользователя | Изменить имя владельца JWT; профиль второго пользователя полностью совпадает с исходным | Высокая | Покрыто | [test_update_profile_changes_only_current_user](../tests/users/test_profile.py) |
| PRF-005 | <a id="prf-005"></a>Чужой нормализованный email → `409 EMAIL_EXISTS`; ни одно поле запроса не сохраняется | `original`, `uppercase`, `spaces`, `both`; вместе переданы новые имя и телефон | Высокая | Покрыто | [test_update_profile_rejects_existing_email](../tests/users/test_profile.py) |
| PRF-006 | <a id="prf-006"></a>Лишние и защищённые поля → `422 VALIDATION_ERROR` нужного поля; сопутствующее имя не сохраняется | По одному: `role`, `is_active`, `password`, `password_hash`, `id`, `user_id`, `created_at`, `updated_at`, `unexpected` | Высокая | Покрыто | [test_update_profile_rejects_forbidden_fields](../tests/users/test_profile.py) |
| PRF-007 | <a id="prf-007"></a>PATCH без корректного JWT → `401 UNAUTHORIZED`, `WWW-Authenticate: Bearer`; профиль сохранён | Нет заголовка, пустой Bearer, `invalid-token`; попытка изменить имя | Высокая | Покрыто | [test_update_profile_requires_authorization](../tests/users/test_profile.py) |
| PRF-008 | <a id="prf-008"></a>Деактивация закрывает GET и PATCH с ранее выданным JWT → `401 UNAUTHORIZED` | Следующий GET; попытка изменить имя через PATCH; заголовок Bearer проверяется для PATCH | Высокая | Покрыто | [test_disabled_user_cannot_use_existing_token](../tests/auth/test_auth_flow.py), [test_disabled_user_cannot_update_profile](../tests/users/test_profile.py) |
| PRF-009 | <a id="prf-009"></a>После реактивации прежний неистёкший JWT снова открывает профиль → `200` | Цепочка GET `200` → деактивация → GET `401` → реактивация → GET `200`; ID/email/имя сохранены, новый вход успешен | Высокая | Покрыто | [test_reactivated_user_can_use_existing_token_and_login](../tests/auth/test_auth_flow.py) |
| PRF-010 | <a id="prf-010"></a>`phone=null` очищает установленный телефон → `200`; остальные поля сохранены | Сначала непустой телефон, затем явный `null` | Средняя | Покрыто | [test_update_profile_can_clear_phone](../tests/users/test_profile.py) |
| PRF-011 | <a id="prf-011"></a>Собственный нормализованный email не считается дубликатом → `200` | `original`, `uppercase`, `spaces`, `both`; значения остальных полей сохранены | Средняя | Покрыто | [test_update_profile_with_own_email](../tests/users/test_profile.py) |
| PRF-012 | <a id="prf-012"></a>Граница длины email после обрезки: 254 → `200`, 255 → `422 VALIDATION_ERROR` поля `body.email` | Для обеих длин: `exact`, `with_outer_spaces` | Средняя | Покрыто | [test_update_profile_with_max_email_length](../tests/users/test_profile.py), [test_update_profile_rejects_email_exceeding_max_length](../tests/users/test_profile.py) |
| PRF-013 | <a id="prf-013"></a>Неверные формат/символы email → `422 VALIDATION_ERROR` поля `body.email` | Пустой/пробельный, без @/домена/локальной части; пять вариантов `INVALID_EMAIL_CHARACTER_CASES`; с запрещёнными символами также передано корректное имя | Средняя | Частично: display name, CJK/emoji, перенос строки и остальные управляющие символы отдельно не проверены | [test_update_profile_rejects_invalid_values](../tests/users/test_profile.py), [test_update_profile_rejects_invalid_email_characters](../tests/users/test_profile.py) |
| PRF-014 | <a id="prf-014"></a>Имя обрезается по краям, длина после обрезки 1–100; неверное → `422 VALIDATION_ERROR` поля `body.name` | Принимаются обычное, 1/100 символов с пробелами по краям, кириллица, внутренний пробел; отклоняются пустое, пробельное, 101 символ | Средняя | Покрыто | [test_update_profile_single_field](../tests/users/test_profile.py), [test_update_profile_rejects_invalid_values](../tests/users/test_profile.py) |
| PRF-015 | <a id="prf-015"></a>Телефон: 7–15 цифр с необязательным плюсом → `200`; неверные длина/формат → `422 VALIDATION_ERROR` поля `body.phone` | 7/15 и 6/16 цифр ±плюс; отказы: пустой/пробельный, буквы, пробел, дефис, скобки, двойной/конечный плюс, полноширинные цифры | Средняя | Покрыто | [test_update_profile_single_field](../tests/users/test_profile.py), [test_update_profile_rejects_invalid_values](../tests/users/test_profile.py) |
| PRF-016 | <a id="prf-016"></a>`email=null` и `name=null` → `422 VALIDATION_ERROR` с указанием поля | Отдельный `null` каждого поля; профиль сохранён | Средняя | Частично: для `name=null` не проверяется поле в `details` | [test_update_profile_rejects_invalid_values](../tests/users/test_profile.py) |
| PRF-017 | <a id="prf-017"></a>Нестроковые значения полей → `422 VALIDATION_ERROR` нужного поля | `email`, `name`, `phone` × integer, float, true, false, array, object | Средняя | Покрыто | [test_update_profile_rejects_invalid_types](../tests/users/test_profile.py) |
| PRF-018 | <a id="prf-018"></a>PATCH требует непустой JSON-объект → `422 VALIDATION_ERROR` при нарушении | Пустой объект `{}`, сломанный JSON, массив `[]`; схема ошибки и сохранность профиля | Средняя | Покрыто | [test_update_profile_rejects_invalid_body](../tests/users/test_profile.py) |
| PRF-019 | <a id="prf-019"></a>Ошибка PATCH соблюдает общий контракт и не отражает пароль/токен | Запрещённое поле `password` вместе с именем → `422`; `body.password`, схема, request ID, секретные значения отсутствуют | Средняя | Покрыто | [test_update_profile_validation_error_response](../tests/users/test_profile.py) |
| PRF-020 | <a id="prf-020"></a>Отсутствующее тело и JSON `null` вместо объекта PATCH → `422 VALIDATION_ERROR`, профиль сохранён | Запрос без тела; тело целиком `null` | Средняя | Не покрыто | — |

Отказы GET при отсутствии/пустом/повреждённом JWT и неверной подписи описаны в [JWT и правах](#authorization). PRF-008 не доказывает сохранность профиля после отклонённого PATCH отключённого пользователя: повторного чтения в этом тесте нет.

Требования закреплённой версии разрешают `null` только для телефона. Ранее здесь было отмечено расхождение с OpenAPI, допускавшей `null` для email/имени; версия той схемы не установлена, актуальность расхождения не подтверждена. Ожидания матрицы основаны на FR-01 и REST-спецификации.

<a id="authorization"></a>

## JWT и права

Источники: FR-01–03, FR-10 и REST-спецификация. Для отказов в доступе передаются корректные данные операции и существуют целевые ресурсы. Высокая важность связана с риском раскрытия данных и выполнения чужих или административных действий. Статус относится только к перечисленным операциям и вариантам токена.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| AUT-001 | <a id="aut-001"></a>Без корректного JWT защищённый запрос → `401 UNAUTHORIZED`, `WWW-Authenticate: Bearer`; действующий токен продолжает открывать профиль | GET профиля и POST отеля × `missing`, `empty`, `malformed`; переданный непустой токен не отражён в ответе | Высокая | Покрыто | [test_protected_operations_reject_invalid_credentials](../tests/auth/test_authorization.py) |
| AUT-002 | <a id="aut-002"></a>JWT с повреждённой подписью → `401 UNAUTHORIZED`, `WWW-Authenticate: Bearer`; исходный токен остаётся рабочим | GET профиля и POST отеля; изменён первый байт подписи, формат base64url и исходные claims сохранены; токен не отражён в ответе | Высокая | Покрыто | [test_protected_operations_reject_invalid_credentials](../tests/auth/test_authorization.py) |
| AUT-003 | <a id="aut-003"></a>Административные операции с пользователями без корректного JWT → `401 UNAUTHORIZED`; пользователь не изменён | Список, детали, PATCH роли × нет токена / `invalid-token`; `WWW-Authenticate: Bearer` | Высокая | Покрыто | [test_admin_user_operations_require_valid_token](../tests/users/test_admin_users.py) |
| AUT-004 | <a id="aut-004"></a>Права определяются актуальной ролью: повышение и понижение применяются к прежнему JWT | GET списка пользователей: `user` → `403 FORBIDDEN`, после повышения → `200`, после понижения → `403 FORBIDDEN`; собственный профиль доступен и совпадает с результатом понижения | Высокая | Покрыто | [test_role_changes_apply_to_existing_token](../tests/users/test_admin_users.py) |
| AUT-005 | <a id="aut-005"></a>Обычный пользователь не создаёт отели и номера → `403 FORBIDDEN`; новые ресурсы не появляются | POST отеля: пустая выборка по уникальному городу до/после; POST номера: список номеров отеля не изменён | Высокая | Покрыто | [test_user_cannot_create_hotel](../tests/auth/test_admin_operations_access.py), [test_user_cannot_create_room](../tests/auth/test_admin_operations_access.py) |
| AUT-006 | <a id="aut-006"></a>Обычный пользователь не меняет и не архивирует каталог → `403 FORBIDDEN`; ресурсы сохранены | Отель: PUT / DELETE, сохранены отель и его номер; номер: PUT / отключение / DELETE, сохранён номер | Высокая | Покрыто | [test_user_cannot_modify_hotel](../tests/auth/test_admin_operations_access.py), [test_user_cannot_modify_room](../tests/auth/test_admin_operations_access.py) |
| AUT-007 | <a id="aut-007"></a>Обычный пользователь не читает административный список и детали пользователей → `403 FORBIDDEN` | Список; детали себя / другого пользователя; контрольные запросы admin → `200` | Высокая | Покрыто | [test_user_cannot_list_users_as_admin](../tests/auth/test_admin_operations_access.py), [test_user_cannot_read_user_as_admin](../tests/auth/test_admin_operations_access.py) |
| AUT-008 | <a id="aut-008"></a>Обычный пользователь не меняет роль/активность через admin PATCH → `403 FORBIDDEN`; профиль цели не изменён | Цель self / other × повышение до admin / отключение; чтение через admin и JWT цели после отказа | Высокая | Покрыто | [test_user_cannot_change_role_or_activity_as_admin](../tests/auth/test_admin_operations_access.py) |
| AUT-009 | <a id="aut-009"></a>Истёкший JWT не открывает защищённый ресурс → `401 UNAUTHORIZED`, `WWW-Authenticate: Bearer` | GET профиля после истечения срока; корректная подпись, существующий активный пользователь | Высокая | Не покрыто | — |
| AUT-010 | <a id="aut-010"></a>JWT отсутствующего пользователя не открывает защищённый ресурс → `401 UNAUTHORIZED` | GET профиля; корректно подписанный неистёкший JWT, пользователь из `sub` отсутствует | Высокая | Не покрыто | — |
| AUT-011 | <a id="aut-011"></a>Выданный JWT использует HS256, содержит `sub`, `iat`, `exp`, `iss`, `aud`, срок действия — 60 минут | Токен успешного входа, `sub` соответствует пользователю; проверка заголовка и содержимого JWT | Средняя | Не покрыто | — |
| AUT-012 | <a id="aut-012"></a>Деактивация действует с проверки активности: уже авторизованный запрос может завершиться, последующий доступ запрещён | Управляемая остановка запроса после авторизации, затем деактивация; завершение само по себе допустимо; новый запрос → `401 UNAUTHORIZED` | Высокая | Не покрыто | — |

Выдача рабочего токена и `expires_in=3600` описаны в [LOG-001](#log-001); это не проверка содержимого JWT или его истечения. Деактивация/реактивация с прежним токеном — [PRF-008](#prf-008), [PRF-009](#prf-009); отказ PATCH профиля без корректного токена — [PRF-007](#prf-007).

<a id="booking-payment-empty-auth"></a>

Бронирования и платежи: отсутствие заголовка и пустой Bearer — [ACC-006–008](testing-bookings.md#acc-006), отмена — [CAN-008](testing-booking-lifecycle.md#can-008); список броней с отсутствующим, пустым, повреждённым токеном и неверной подписью — [ACC-009](testing-bookings.md#acc-009). Доступ к чужим ресурсам описан в [матрице прав на брони и платежи](testing-bookings.md#booking-access-checklist).

<a id="admin-operations-access"></a>

Запрет административных действий обычному пользователю — [AUT-005](#aut-005)–[AUT-008](#aut-008). Проверки доступа к архивному каталогу остаются в [документе каталога](testing-hotels.md).

<a id="admin-users"></a>

## Администрирование пользователей

Источники: FR-01, FR-02, FR-10 и REST-спецификация. Общие условия: действующий JWT admin и отдельный тестовый пользователь; для ADM-003 — изолированный стенд с единственным активным admin. Высокая важность изменений связана с риском потери административного доступа и нежелательного изменения учётной записи. После отклонённых PATCH и конфликтов ниже пользователь повторно читается и сравнивается с исходным, кроме непокрытых сценариев.

| ID | Проверяемое правило | Варианты | Важность | Покрытие | Реализация автотеста |
| --- | --- | --- | --- | --- | --- |
| ADM-001 | <a id="adm-001"></a>Admin меняет роль и активность одним PATCH → `200`; остальные данные сохранены | `role=admin`, `is_active=false`; ID/email/имя/телефон/created_at не изменены, GET совпадает с PATCH | Высокая | Покрыто | [test_admin_can_change_role_and_activity_together](../tests/users/test_admin_users.py) |
| ADM-002 | <a id="adm-002"></a>Невалидный admin PATCH → `422 VALIDATION_ERROR`, без частичного изменения | `{}`; null каждого поля; `role=owner` / число; `is_active` строка `false` / 0 / массив; запрещённые email/password; корректная роль вместе с unknown-полем или `is_active=null` | Высокая | Покрыто | [test_admin_patch_rejects_invalid_fields_without_partial_update](../tests/users/test_admin_users.py) |
| ADM-003 | <a id="adm-003"></a>Последний активный admin сохраняется → `409 LAST_ACTIVE_ADMIN`, исходный профиль и единственный admin остаются | PATCH себя: понижение роли / отключение / оба действия; последовательные варианты на изолированном стенде | Высокая | Покрыто | [test_last_active_admin_cannot_be_removed](../tests/users/test_last_admin.py) |
| ADM-004 | <a id="adm-004"></a>При конкурентных изменениях сохраняется хотя бы один активный admin | Два активных admin одновременно теряют роль или активность; итоговый список содержит активного admin | Высокая | Не покрыто | — |
| ADM-005 | <a id="adm-005"></a>Admin читает пользователя → `200`, данные совпадают с созданным пользователем, секреты не раскрываются | Отдельный активный `user`; нет полей password/password_hash и исходного пароля в тексте; есть X-Request-ID | Средняя | Покрыто | [test_admin_reads_user_without_secrets](../tests/users/test_admin_users.py) |
| ADM-006 | <a id="adm-006"></a>Список фильтруется по роли и активности → `200`, содержит целевого пользователя, элементы без пароля/хеша | Совместные фильтры `role=user/admin` × `is_active=true/false`; все элементы соответствуют обоим фильтрам, `total>=1`, limit=100 | Средняя | Покрыто | [test_admin_list_filters_include_matching_user](../tests/users/test_admin_users.py) |
| ADM-007 | <a id="adm-007"></a>Сортировка списка: основное поле в заданном направлении, при равенстве UUID возрастает | Без sort (created_at); ±created_at, ±email; limit=100 | Средняя | Частично: порядок основного поля проверяется, совпадающие значения для проверки UUID не обеспечены данными | [test_admin_list_sorting](../tests/users/test_admin_users.py) |
| ADM-008 | <a id="adm-008"></a>Пагинация согласована с исходной выборкой; за её концом пусто, defaults 20/0 | До четырёх элементов при sort=email; limit=2, offset=0/2, одинаковый total, нет повторяющихся ID; offset=total → items=[]; запрос без параметров | Средняя | Покрыто | [test_admin_list_pagination](../tests/users/test_admin_users.py) |
| ADM-009 | <a id="adm-009"></a>Невалидные параметры списка → `422 VALIDATION_ERROR` с нужным `query.*` в details | limit=0/101/`bad`, offset=-1, role=owner, is_active=bad | Средняя | Покрыто | [test_admin_list_rejects_invalid_query](../tests/users/test_admin_users.py) |
| ADM-010 | <a id="adm-010"></a>Неподдерживаемая сортировка → `422 INVALID_SORT` | sort=role | Средняя | Покрыто | [test_admin_list_rejects_unknown_sort](../tests/users/test_admin_users.py) |
| ADM-011 | <a id="adm-011"></a>Неизвестный UUID → `404 NOT_FOUND`, некорректный ID → `422 VALIDATION_ERROR` | GET деталей / PATCH активности × случайный UUID / `not-a-uuid` | Средняя | Покрыто | [test_admin_user_rejects_unknown_or_invalid_id](../tests/users/test_admin_users.py) |
| ADM-012 | <a id="adm-012"></a>Некорректное JSON-тело PATCH → `422 VALIDATION_ERROR`, пользователь сохранён | Сломанный JSON, массив `[]` | Средняя | Покрыто | [test_admin_patch_rejects_invalid_json](../tests/users/test_admin_users.py) |
| ADM-013 | <a id="adm-013"></a>Отсутствующее тело и JSON `null` вместо объекта PATCH → `422 VALIDATION_ERROR`, пользователь сохранён | Запрос без тела; тело целиком `null` | Средняя | Не покрыто | — |
| ADM-014 | <a id="adm-014"></a>Деактивация не меняет сроки и жизненный цикл броней | Отключить владельца: pending_payment удерживает даты до прежнего срока и затем истекает; confirmed сохраняется до выезда, затем completed; платёж изменяется по общим правилам | Высокая | Не покрыто | — |

Изменение одной роли и применение к прежнему JWT — [AUT-004](#aut-004); деактивация/реактивация и доступ к профилю — [PRF-008–009](#prf-008), сохранение брони/платежа — [ACC-011](testing-bookings.md#acc-011). Отказы без корректного JWT и для обычного пользователя — [AUT-003](#aut-003), [AUT-007–008](#aut-007). В ADM-006 проверяются совместные фильтры, в ADM-008 наличие четырёх пользователей не гарантируется; это не полный перебор фильтров и границ пагинации.

### Отдельный запуск защиты последнего admin

[ADM-003](#adm-003) содержит три параметризованных варианта одной функции с меткой `isolated_admin`. Конкурентный сценарий ADM-004 пока не реализован.

В CI эти проверки выполняются в конце `full`. Локально скрипт поднимает временный API и PostgreSQL и оставляет на этом стенде одного активного администратора. [Запуск приложения через Compose](README.md#запуск-отдельного-приложения) подготавливает нужные Docker-образы.

Выполните команду из корня репозитория автотестов.

```powershell
.\.venv\Scripts\python.exe scripts/run_last_admin_tests.py
```
