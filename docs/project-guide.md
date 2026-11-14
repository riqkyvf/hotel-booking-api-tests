# Навигатор по основным сценариям

Начни с первой строки таблицы и переходи дальше после разбора одного теста. Для каждого сценария здесь указаны точная функция, подготовка данных и смысл проверок. Чтобы найти функцию в открытом файле, скопируй её имя в поиск редактора.

Это порядок изучения. Каждый тест готовит свои данные и может выполняться отдельно; результаты предыдущих строк ему не нужны. Здесь описана текущая реализация выбранных тестов. Полная карта операций находится в [карте покрытия API](README.md#карта-покрытия-api), источники ожидаемого поведения — в [разделе о контракте](README.md#контракт).

## 1. Шесть тестов для начала

| № | Проверяемое правило | Файл и точная функция | Что готовится до тела теста | Что проверяется в тесте |
| --- | --- | --- | --- | --- |
| 1 | Зарегистрированный пользователь может войти и прочитать собственный профиль | [test_auth_flow.py](../tests/auth/test_auth_flow.py), `test_registered_user_can_login_and_get_profile` | `registered_user` регистрирует нового пользователя | Login возвращает `200` и непустой строковый токен. GET профиля возвращает `200`, данные созданного пользователя, роль `user`, активность и отсутствие пароля/хеша |
| 2 | Доступный номер можно найти и получить стоимость выбранного проживания | [test_booking_flow.py](../tests/bookings/test_booking_flow.py), `test_user_can_select_available_room` | `available_room` создаёт отель и номер; `stay_dates` задаёт даты и гостей | Номер присутствует в списке и читается по ID. Доступность равна `true`, причина отказа отсутствует. Число ночей, сумма и валюта соответствуют данным сценария |
| 3 | Новая бронь принадлежит создавшему её пользователю и доступна для чтения | [test_booking_flow.py](../tests/bookings/test_booking_flow.py), `test_user_can_create_and_read_booking` | Новый пользователь с токеном, отдельный отель и номер, даты проживания | POST возвращает `201`, статус `pending_payment`, правильные поля и сумму; `expires_at` находится в будущем. GET и список возвращают эту бронь. Точную длительность удержания этот тест не проверяет |
| 4 | Успешная тестовая оплата подтверждает бронь | [test_booking_flow.py](../tests/bookings/test_booking_flow.py), `test_user_can_pay_for_booking` | Новый пользователь с токеном, отдельный отель и номер, даты проживания | В теле теста создаются бронь и платёж. Платёж получает сумму брони; после симуляции успеха GET платежа показывает `succeeded`, GET брони — `confirmed` |
| 5 | Отмена освобождает даты и приводит платёж к соответствующему состоянию | [test_booking_cancellation.py](../tests/bookings/test_booking_cancellation.py), `test_cancellation_releases_room_for_another_user` | `booking_to_cancel` создаёт бронь в одном из трёх вариантов; `second_user` создаёт другого пользователя | До отмены даты заняты; после отмены бронь имеет статус `cancelled`. Ожидающий платёж отменяется, успешный возвращается. Другой пользователь может забронировать те же даты, исходная отменённая бронь сохраняется |
| 6 | Обычный пользователь не может прочитать чужую бронь | [test_booking_access.py](../tests/bookings/test_booking_access.py), `test_user_cannot_read_another_users_booking` | `booking_with_payment` создаёт ресурсы владельца; `second_user` создаёт другого пользователя | Чужой GET получает `404 NOT_FOUND`, список другого пользователя пуст. Владелец продолжает видеть исходную бронь без изменений |

## 2. Какие фикстуры открывать

Фикстура — функция подготовки данных. Pytest находит её по имени аргумента теста, выполняет её зависимости и передаёт возвращённое значение в тест. Общие фикстуры находятся в [tests/conftest.py](../tests/conftest.py).

| Имя | Что делает и что возвращает |
| --- | --- |
| `base_url` | Читает адрес API из настроек и возвращает строку. Используется всеми шестью сценариями |
| `user_data` | Создаёт словарь с уникальным тестовым email, паролем и именем. HTTP-запросов не отправляет |
| `registered_user` | Вызывает `register`, проверяет `201`, возвращает `{"payload": ..., "user": ...}`: отправленные данные и ответ регистрации |
| `registered_login_data` | Берёт email и пароль из `registered_user["payload"]` и возвращает данные для входа |
| `user_access_token` | Выполняет login с `registered_login_data`, проверяет `200`, возвращает строку токена |
| `admin_access_token` | Входит под существующим администратором из настроек. Используется для создания отелей и номеров; сам пользователь сценария остаётся обычным пользователем |
| `available_room` | Через API создаёт новый отель и доступный неархивный номер. Возвращает `{"hotel": ..., "room": ...}` |
| `stay_dates` | Возвращает даты и гостей. Сейчас: заезд через два дня по UTC, три ночи, два гостя. Значения берутся из [data/booking.py](../data/booking.py) |
| `second_user` | Регистрирует ещё одного пользователя с отдельным email и выполняет вход. Возвращает его `id` и `access_token` |
| `pending_payment` | С токеном владельца создаёт бронь и ожидающий платёж. Возвращает `{"booking": ..., "payment": ...}` |
| `booking_with_payment` | Использует `pending_payment` и подготавливает один из двух вариантов: `pending_payment`/`pending` либо `confirmed`/`succeeded`. Поэтому тест № 6 выполняется дважды |
| `booking_to_cancel` | Локальная фикстура в [test_booking_cancellation.py](../tests/bookings/test_booking_cancellation.py). Готовит бронь без платежа, с ожидающим платежом либо с успешным платежом. Возвращает `booking` и `payment`; без платежа значение `payment` равно `None` |

У обычных фикстур в этой таблице область действия — один тестовый случай. Если две зависимости одного случая запрашивают `registered_user`, pytest переиспользует одного подготовленного пользователя. Например, явно переданный в тест № 3 `registered_user` и пользователь, для которого получен `user_access_token`, совпадают. `base_url` имеет область действия на всю сессию.

## 3. Какие запросы стоят за функциями

В таблице указаны пути относительно `base_url`. Функции из `api/` отправляют запрос и возвращают `requests.Response`; проверки результата находятся в тесте или фикстуре подготовки.

| Функция | HTTP-запрос | Где посмотреть |
| --- | --- | --- |
| `register` | `POST /auth/register` | [api/auth.py](../api/auth.py) |
| `login` | `POST /auth/login` | [api/auth.py](../api/auth.py) |
| `get_profile` | `GET /users/me` | [api/users.py](../api/users.py) |
| `create_hotel` | `POST /hotels` | [api/hotels.py](../api/hotels.py) |
| `create_room` | `POST /hotels/{hotel_id}/rooms` | [api/rooms.py](../api/rooms.py) |
| `list_rooms` | `GET /hotels/{hotel_id}/rooms` | [api/rooms.py](../api/rooms.py) |
| `get_room` | `GET /rooms/{room_id}` | [api/rooms.py](../api/rooms.py) |
| `get_room_availability` | `GET /rooms/{room_id}/availability` с датами и гостями | [api/rooms.py](../api/rooms.py) |
| `create_booking` | `POST /bookings` с телом брони и `Idempotency-Key` | [api/bookings.py](../api/bookings.py) |
| `get_booking` | `GET /bookings/{booking_id}` | [api/bookings.py](../api/bookings.py) |
| `list_bookings` | `GET /bookings` | [api/bookings.py](../api/bookings.py) |
| `create_payment` | `POST /bookings/{booking_id}/payments` | [api/payments.py](../api/payments.py) |
| `get_payment` | `GET /payments/{payment_id}` | [api/payments.py](../api/payments.py) |
| `simulate_payment_success` | `POST /payments/{payment_id}/simulate-success` | [api/payments.py](../api/payments.py) |
| `cancel_booking` | `PATCH /bookings/{booking_id}/cancel` | [api/bookings.py](../api/bookings.py) |

## 4. Первый тест: конкретный маршрут чтения

Открой [test_auth_flow.py](../tests/auth/test_auth_flow.py) и найди `test_registered_user_can_login_and_get_profile`. Для первого разбора достаточно этой функции и её зависимостей.

1. Посмотри аргументы `base_url, registered_user`. Это значения, которые подготовит pytest перед выполнением тела теста.
2. В [conftest.py](../tests/conftest.py) найди `registered_user`. Она зависит от `base_url` и `user_data`.
3. Прочитай `user_data`: она собирает данные нового пользователя. Затем вернись в `registered_user`: там вызывается `register` и проверяется успешная регистрация.
4. В [api/auth.py](../api/auth.py) найди `register`. Проследи, как словарь данных передаётся в `requests.post` через `json=data`.
5. Вернись в тест. `registered_user["payload"]` содержит отправленные при регистрации данные; из них тест берёт email и пароль для `login`. Здесь вход выполняется прямо в тесте, фикстура `user_access_token` ему не нужна.
6. Ответ login хранится в `login_response`. `status_code` — HTTP-статус; `.json()` разбирает JSON-тело ответа. Из тела извлекается `access_token`.
7. В [api/users.py](../api/users.py) прочитай `get_profile`, затем в [api/headers.py](../api/headers.py) — `authorization_headers`: токен передаётся как `Authorization: Bearer ...`.
8. Вернись к assertions профиля. ID сравнивается с `registered_user["user"]["id"]` — ID из ответа регистрации. Email и имя сравниваются с отправленными данными. Остальные проверки подтверждают значения по умолчанию и отсутствие секретных полей.

Для этого сценария цепочка выглядит так:

```text
Подготовка pytest:
  base_url + user_data → registered_user → POST регистрации → 201

Тело теста:
  email/password → POST login → 200 + токен
  токен → GET профиля → 200 + проверка данных пользователя
```

`allure.step(...)` обозначает шаг в отчёте. Проверки выполняются выражениями `assert`; если условие ложно, выполнение этой проверки завершается ошибкой.

## 5. Что заметить при переходе к следующим тестам

- **№ 2:** раскрой `available_room` и `stay_dates`. Сопоставь возвращённые словари с тем, что тест читает через `[...]`. Исходные параметры номера находятся в [data/booking.py](../data/booking.py), отеля — в [data/hotels.py](../data/hotels.py).
- **№ 3:** проследи, как `payload` собирается из `room_id` и `stay_dates`. `uuid4().hex` создаёт ключ для запроса бронирования. `Decimal` нужен для десятичного денежного расчёта. При текущих данных ожидается `1234.56 × 3 = 3703.68 RUB`.
- **№ 4:** отдельно выпиши состояния до и после оплаты: бронь `pending_payment → confirmed`, платёж `pending → succeeded`. В этом тесте подготовка брони и платежа видна прямо в теле функции.
- **№ 5:** прочитай локальную фикстуру `booking_to_cancel` и `CANCELLATION_PAYMENT_CASES` в [data/booking.py](../data/booking.py). Параметризация даёт три самостоятельных случая: без платежа; `pending → cancelled`; `succeeded → refunded`. Сначала разбери вариант `without_payment`, затем два остальных.
- **№ 6:** различай токен владельца и токен `second_user`. Прочитай [assert_api_error](../tests/assertions.py): она проверяет статус, схему ошибки, её код и совпадение request ID тела и заголовка. `404` для чужой брони предусмотрен контрактом приватных ресурсов.

## 6. Как проверить своё понимание

После одного сценария попробуй объяснить пять вещей: какое правило проверяется; что подготовлено до теста; какой запрос выполняет проверяемое действие; откуда берётся ожидаемый результат; какую ошибку обнаружит каждый основной `assert`.

Если какой-то ответ не получается, вернись к соответствующему месту из таблиц. Для начала достаточно полностью разобрать сценарий № 1. Изучение остальных файлов, SQL и конкурентных сценариев можно продолжить после этого маршрута.
