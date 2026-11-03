# Полный прогон после точечного рефакторинга

Дата: 03.11.2026 (Asia/Irkutsk).

## Результат

**501 passed за 179.94 с**, 0 failures, 0 errors, 0 skipped. Выполнены все 17 модулей, включая тест с меткой `db`. Результат подтверждён JUnit XML, а не только сборкой тестов.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=junit-architecture-refactor.xml
```

JUnit: `junit-architecture-refactor.xml` в корне проекта, исключён из Git существующим правилом. SHA-256 отчёта: `fdb565b4db6b3be7aa00aa94ac3d1a8fc43e9637ab403c3a1dddff20d81d8b6d`.

Начальная попытка в ограниченной среде прервана из-за запрета сетевого доступа Windows (`WinError 10013`). Итог выше относится к завершённому повторному запуску с доступом к локальному стенду.

## Проверенные изменения

- `api/headers.py`: единая функция `authorization_headers`. `None` не отправляет Authorization, пустая строка отправляет пустой Bearer; остальные значения передаются без нормализации.
- Все 18 API-функций с авторизацией используют эту функцию. Idempotency-Key и Content-Type сохраняются.
- `tests/assertions.py`: общий контракт ошибки (статус, JSON Schema, код, наличие и совпадение request ID).
- 38 повторяющихся блоков в 13 модулях заменены `assert_api_error`. Конкретные поля, WWW-Authenticate, проверки секретов и последствий операции остались в сценариях.
- `tests/__init__.py`: явный пакет для импорта помощника.

Дополнительно выполнены локальные проверки без обращения к стенду: три режима токена; отсутствие Authorization во всех 18 функциях; принятие корректного ответа помощником и отклонение неверных статуса, кода, схемы и request ID. Статическая сверка подтвердила сохранение количества assert с учётом вынесенных четырёх проверок на каждый вызов помощника. `git diff --check` пройден.

## Версии и границы воспроизводимости

- Python: **3.14.2**.
- Базовый commit тестов: `a3e4e70484142ce6a2b18c85a7ce1b2570aaf4c9`. Прогон выполнен с незакоммиченными изменениями, описанными выше; это не результат чистого commit.
- Отпечаток проверенных исходников и конфигурации: `81e2ab2ee63a79b4f69df0d5c917dee82a1d3b03ef832f22397f6a82571d034b`. Алгоритм: SHA-256 UTF-8-манифеста ниже; пути отсортированы, каждая строка имеет вид `sha256  path` и заканчивается LF. `.env` и секреты в отпечаток не входят.
- API: локальный стенд `http://localhost:8000/api/v1`, контейнер `hotel-booking-api-1`, образ `hotel-booking-api`.
- ID запущенного образа API: `sha256:07089aeb01e4eba54350c711176bacf8a125627dbe40a9a86cb1c93af70ec50b`.
- Время создания образа: `2026-11-03T05:52:16.290112981Z`; подключённых томов у контейнера API нет.
- Контейнеры стенда: `hotel-booking-api-1`, `hotel-booking-worker-1`, `hotel-booking-db-1`; БД использует образ `postgres:17-alpine`.
- HEAD локального репозитория приложения: `a515cdb5deffac1106839aa78d3e3bb1171dbe51`; есть изменения в `app/schemas/__init__.py`, `docs/api-specification.md`, `docs/database-schema.md`, `docs/requirements.md`. Соответствие этого HEAD исходникам запущенного образа не подтверждено; для идентификации исполняемого API используется ID образа выше.
- БД перед прогоном не сбрасывалась; созданные тестами данные остаются согласно существующей стратегии проекта. Результат не подтверждает параллельный запуск и не является проверкой другого образа приложения.

## Манифест проверенных файлов

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
