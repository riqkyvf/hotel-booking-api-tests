# Чек-лист изменения профиля

Операция: `PATCH /api/v1/users/me`. Окружение: отдельный локальный стенд. Дата: 03.11.2026.

Основания: [FR-01 и FR-02](requirements.md#fr-01-пользователи-и-авторизация), [контракт API](api-specification.md#авторизация-и-профиль). Поля изменения — email, name, phone; хотя бы одно обязательно. `null` разрешён только для телефона. Правила ASCII относятся к email; кириллица в имени допустима.

HTTP-прогон модуля от 03.11.2026: **105 passed за 33.37 с**. Локальный отчёт — `junit-profile.xml` (исключён из Git). Полный регрессионный прогон — **431 passed за 114.06 с**, отчёт `junit.xml`. Всего 17 пунктов чек-листа, каждый подтверждён прошедшими тестами; число пунктов не равно числу параметризованных случаев.

| ID | Проверка | Ожидаемый результат | Статус | Автотест |
|---|---|---|---|---|
| PRF-001 | Изменить все поля, включая plus-tag и ASCII Punycode-домен | 200; нормализация; GET подтверждает сохранение; ID, роль и активность сохранены; вход работает с новым email, старый даёт 401 | Passed | [test_update_profile_all_fields](../tests/test_profile.py#L41) |
| PRF-002 | Отдельно изменить имя или телефон, проверить границы | 200; имя обрезается до проверки длины; имя 1/100 символов и телефон 7/15 цифр с/без + допустимы; пропущенные поля сохранены | Passed | [test_update_profile_single_field](../tests/test_profile.py#L82) |
| PRF-003 | Изменить только имя после установки email и телефона | 200; ранее сохранённые email и телефон не сбрасываются | Passed | [test_update_profile_preserves_omitted_fields](../tests/test_profile.py#L101) |
| PRF-004 | Очистить ранее установленный телефон через null | 200; телефон null в PATCH и GET; остальные данные сохранены | Passed | [test_update_profile_can_clear_phone](../tests/test_profile.py#L123) |
| PRF-005 | Email 254 символа, с крайними обычными пробелами и без них | 200; длина считается после обрезки; GET подтверждает нормализованный адрес | Passed | [test_update_profile_with_max_email_length](../tests/test_profile.py#L141) |
| PRF-006 | Передать собственный email в исходном виде, верхнем регистре, с пробелами и их сочетанием | 200; email нормализован; конфликта с собой нет | Passed | [test_update_profile_with_own_email](../tests/test_profile.py#L158) |
| PRF-007 | Email другого пользователя, включая варианты нормализации; одновременно валидные имя и телефон | 409 EMAIL_EXISTS; ошибка соответствует ERROR_SCHEMA; GET показывает исходный профиль без частичных изменений | Passed | [test_update_profile_rejects_existing_email](../tests/test_profile.py#L177) |
| PRF-008 | Общая матрица недопустимых символов email | 422 VALIDATION_ERROR, body.email; валидное имя из того же запроса не сохраняется | Passed | [test_update_profile_rejects_invalid_email_characters](../tests/test_profile.py#L205) |
| PRF-009 | Null имени/email; неверные формат и длина email, имени, телефона | 422 VALIDATION_ERROR; профиль не меняется; путь поля проверяется там, где это полевая ошибка | Passed | [test_update_profile_rejects_invalid_values](../tests/test_profile.py#L223) |
| PRF-010 | Числа, boolean, массивы и объекты для каждого поля | 422 VALIDATION_ERROR с путём поля; профиль не меняется | Passed | [test_update_profile_rejects_invalid_types](../tests/test_profile.py#L241) |
| PRF-011 | Передать роль, активность, пароль, хеш, ID, user_id, timestamps или неизвестное поле | 422 VALIDATION_ERROR; валидное изменение имени из того же запроса также не сохраняется | Passed | [test_update_profile_rejects_forbidden_fields](../tests/test_profile.py#L257) |
| PRF-012 | Нет тела, пустой объект, сломанный JSON или тело другого типа | 422 VALIDATION_ERROR в едином формате; профиль не меняется | Passed | [test_update_profile_rejects_invalid_body](../tests/test_profile.py#L275) |
| PRF-013 | Email 255 символов, с крайними пробелами и без них | 422 VALIDATION_ERROR, body.email; профиль не меняется | Passed | [test_update_profile_rejects_email_exceeding_max_length](../tests/test_profile.py#L290) |
| PRF-014 | Нет Authorization, пустой Bearer или некорректный токен | 401 UNAUTHORIZED; WWW-Authenticate: Bearer; профиль не меняется | Passed | [test_update_profile_requires_authorization](../tests/test_profile.py#L308) |
| PRF-015 | Отключить пользователя после выдачи токена, затем изменить профиль | 401 UNAUTHORIZED со старым токеном | Passed | [test_disabled_user_cannot_update_profile](../tests/test_profile.py#L322) |
| PRF-016 | Изменить профиль, когда в стенде есть второй пользователь | Меняется только текущий пользователь; профиль второго остаётся прежним | Passed | [test_update_profile_changes_only_current_user](../tests/test_profile.py#L341) |
| PRF-017 | Ошибка с паролем-маркером в запрещённом поле | 422; ERROR_SCHEMA; X-Request-ID совпадает с error.request_id; пароль и токен не отражаются; профиль не меняется | Passed | [test_update_profile_validation_error_response](../tests/test_profile.py#L364) |

## Известные ограничения

- В живой OpenAPI-схеме email и name допускают null через anyOf, но runtime-валидация и нормативные требования запрещают явный null. Это несоответствие схемы приложения; тесты не ослабляют контракт ради него. Для null имени проверяется отказ и отсутствие изменений без привязки к недокументированному пути модельной ошибки.
- Сохранность данных проверяется через GET API, без SQL. Хеш пароля и отсутствие прямых изменений в БД отдельно не проверяются.
- Истёкший JWT, неверные подпись/iss/aud, конкурентные PATCH, изменение профиля администратором и полная валидация ID/timestamps успешного ответа пока не покрыты этим модулем.
- Версия запущенного приложения пока не зафиксирована. Тесты не используют общие seed-профили и не сбрасывают БД.
