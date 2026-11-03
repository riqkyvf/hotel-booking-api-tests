# Каталог отелей

Сценарии, ограничения и связь с автотестами. ID проверок сохранены. Число пунктов не равно числу параметризованных случаев. Последний полный прогон: **501 passed за 179.99 с**; [журнал](test-runs.md). Passed / Partial / Not run описывают объём проверки пункта: успешный прогон набора не закрывает непокрытые части. Исторические сведения о версиях и результаты отдельных этапов вынесены в журнал.

- [Чек-лист чтения каталога отелей](#hotels-checklist)

<a id="hotels-checklist"></a>

## Чек-лист чтения каталога отелей

Дата составления: 03.11.2026. Операции: `GET /api/v1/hotels` и `GET /api/v1/hotels/{hotel_id}`.

Основания: [FR-03](requirements.md#fr-03-каталог), [контракт отелей](api-specification.md#отели), ограничения query-параметров в OpenAPI. Первый блок покрывает чтение каталога; ценовой блок ниже добавлен после согласования правила минимальной цены.

<a id="hotels-checklist-подготовка-и-изоляция"></a>

### Подготовка и изоляция

- Для каждого теста, которому нужны данные, создаются собственные отели через административный POST API. Город содержит UUID и изолирует выборку от seed и предыдущих прогонов.
- Основная выборка: четыре отеля с именами Beta, Alpha, Alpha, Omega и рейтингами 0.0, 3.0, 3.0, 5.0. Одинаковые имя и рейтинг позволяют проверить дополнительную сортировку по UUID.
- Дополнительный отель находится в городе с общим префиксом и другим полным названием. Это проверяет точное сравнение города.
- Для деталей создаётся один отель; полная выборка каталога этим тестам не нужна. Архивный отель создаётся и архивируется через административный API только для сценариев архивности.
- Создание и архивирование здесь служат подготовкой; самостоятельное полное покрытие POST/PUT/DELETE в этот блок не входит. Общие seed-объекты не изменяются, SQL-очистка не выполняется.

<a id="hotels-checklist-get-hotels"></a>

### GET /hotels

| ID | Проверка / варианты | Ожидаемый результат | Статус | Автотест |
|---|---|---|---|---|
| HL-001 | Запрос без авторизации и параметров | 200; items, total, limit, offset; limit=20, offset=0; размер страницы соответствует total/limit; X-Request-ID присутствует | Passed | [test_hotels_default_pagination](../tests/test_hotels.py) |
| HL-002 | Структура страницы и объектов отеля | Обязательные поля и типы соответствуют контракту; rating — десятичная строка; архивные записи в обычной выдаче отсутствуют | Passed | [test_hotels_default_pagination](../tests/test_hotels.py) |
| HL-003 | limit=1, 2, 100; offset=0, 1, 2 | 200; точный состав и порядок соответствующей страницы контролируемой выборки; параметры отражены в ответе | Passed | [test_hotels_pagination](../tests/test_hotels.py) |
| HL-004 | Пагинация одной выборки | total равен числу подходящих отелей до пагинации и не меняется между страницами; страницы покрывают ожидаемую последовательность без пересечений | Passed | [test_hotels_pagination_pages](../tests/test_hotels.py) |
| HL-005 | offset равен размеру выборки или превышает его | 200; items пуст; total остаётся числом подходящих отелей | Passed | [test_hotels_pagination](../tests/test_hotels.py) |
| HL-006 | Несуществующий уникальный город | 200; items=[], total=0 | Passed | [test_hotels_unknown_city](../tests/test_hotels.py) |
| HL-007 | Город исходный, в нижнем/верхнем регистре, с крайними пробелами и сочетанием нормализации | 200; точный состав из четырёх отелей нужного города | Passed | [test_hotels_city_normalization](../tests/test_hotels.py) |
| HL-008 | Город — только часть существующего названия | 200; items=[], total=0; отель соседнего города не включается в точную выборку | Passed | [test_hotels_city_requires_full_match](../tests/test_hotels.py) |
| HL-009 | min_rating и max_rating отдельно, без city | 200; все возвращённые рейтинги удовлетворяют условию; total не меньше числа заведомо подходящих созданных отелей | Passed | [test_hotels_rating_without_city](../tests/test_hotels.py) |
| HL-010 | Нижняя/верхняя границы рейтинга, включая 0 и 5; min=max | 200; границы включены; точный состав по контролируемым данным | Passed | [test_hotels_rating_filter](../tests/test_hotels.py) |
| HL-011 | Комбинация city с диапазоном рейтинга; диапазон без совпадений | Учитываются оба условия; неподходящий город исключён; пустая выборка даёт 200 и total=0 | Passed | [test_hotels_rating_filter](../tests/test_hotels.py) |
| HL-012 | Сортировка по умолчанию, name и -name | 200; ожидаемый порядок имён; default соответствует name | Passed | [test_hotels_sorting](../tests/test_hotels.py) |
| HL-013 | Сортировка rating и -rating | 200; рейтинги по возрастанию/убыванию | Passed | [test_hotels_sorting](../tests/test_hotels.py) |
| HL-014 | Равные имя или рейтинг при обоих направлениях сортировки | Дополнительный порядок — UUID по возрастанию | Passed | [test_hotels_sorting](../tests/test_hotels.py) |
| HL-015 | Гость, user, admin без include_archived и с явным false | Архивный отель скрыт; items/total содержат только четыре неархивных отеля города | Passed | [test_hotels_hide_archived_by_default](../tests/test_hotels.py) |
| HL-016 | Admin и include_archived=true | 200; включены четыре неархивных и один архивный отель; total=5; флаги архивности корректны | Passed | [test_hotels_admin_can_include_archived](../tests/test_hotels.py) |
| HL-017 | Гость и user с include_archived=true | 403 FORBIDDEN; единый формат ошибки и совпадающий request ID | Passed | [test_hotels_archived_list_requires_admin](../tests/test_hotels.py) |
| HL-018 | limit=0, -1, 101; отрицательный offset; нецелые/нечисловые значения | 422 VALIDATION_ERROR; details указывает query-параметр | Passed | [test_hotels_invalid_query_parameters](../tests/test_hotels.py) |
| HL-019 | min/max_rating меньше 0, больше 5 или нечисловые | 422 VALIDATION_ERROR; details указывает query-параметр | Passed | [test_hotels_invalid_query_parameters](../tests/test_hotels.py) |
| HL-020 | min_rating больше max_rating | 422 INVALID_FILTER_RANGE | Passed | [test_hotels_invalid_rating_range](../tests/test_hotels.py) |
| HL-021 | Неизвестное поле сортировки, неизвестное поле с минусом, двойной минус, пустая строка | 422 INVALID_SORT | Passed | [test_hotels_invalid_sort](../tests/test_hotels.py) |
| HL-022 | Некорректная строка include_archived | 422 VALIDATION_ERROR, query.include_archived | Passed | [test_hotels_invalid_query_parameters](../tests/test_hotels.py) |

<a id="hotels-checklist-get-hotelshotel_id"></a>

### GET /hotels/{hotel_id}

| ID | Проверка / варианты | Ожидаемый результат | Статус | Автотест |
|---|---|---|---|---|
| HD-001 | Существующий неархивный отель без токена | 200; точные ID и сохранённые данные; обязательные поля и типы; X-Request-ID | Passed | [test_get_hotel_for_each_role](../tests/test_hotels.py) |
| HD-002 | Тот же сценарий для user и admin | 200; корректные данные отеля | Passed | [test_get_hotel_for_each_role](../tests/test_hotels.py) |
| HD-003 | Случайный корректный UUID без соответствующего отеля | 404 NOT_FOUND | Passed | [test_get_hotel_not_found](../tests/test_hotels.py) |
| HD-004 | Некорректный UUID | 422 VALIDATION_ERROR, path.hotel_id | Passed | [test_get_hotel_invalid_uuid](../tests/test_hotels.py) |
| HD-005 | Архивный отель для гостя и user | 404 NOT_FOUND; данные отеля не возвращаются | Passed | [test_get_archived_hotel_hidden](../tests/test_hotels.py) |
| HD-006 | Архивный отель для admin | 200; правильный ID и данные, is_archived=true | Passed | [test_get_archived_hotel_as_admin](../tests/test_hotels.py) |
| HD-007 | Ошибки 404 и 422 | ERROR_SCHEMA; X-Request-ID присутствует и совпадает с error.request_id | Passed | [test_get_hotel_not_found](../tests/test_hotels.py), [test_get_hotel_invalid_uuid](../tests/test_hotels.py) |

<a id="hotels-checklist-ценовые-фильтры-и-сортировка"></a>

### Ценовые фильтры и сортировка

Согласованное правило: фильтр проверяет наличие одного активного неархивного номера внутри всего диапазона; сортировка использует минимум всех активных неархивных номеров отеля независимо от диапазона.

Подготовка: собственные отели в уникальном городе; активные номера с ценами 0.01, 1000, 6500, 7000, 9000, 10000 и 9999999999.99. Отдельные отели имеют только отключённые, только архивные номера или не имеют номеров. В одном отеле есть дорогой активный номер и более дешёвые отключённый/архивный. Два отеля имеют одинаковую минимальную цену. Отель другого города нужен для проверки комбинаций фильтров. Номера создаются и меняют состояние через административный API; эти операции служат подготовкой.

Полная выборка из девяти отелей нужна только для матрицы ценовых фильтров. Остальные сценарии создают меньшие наборы: три отеля для числовой сортировки, два и соседний город для комбинаций фильтров, пять для пагинации, четыре для порядка отелей без цены. Общая функция подготовки создаёт один отель с номерами; ожидаемый состав и порядок задаются явно через именованные ключи. Равные цены и порядок UUID проверяются при пагинации, отсутствие цены — отдельным тестом. Все 14 пунктов HP подтверждены последним прогоном, указанным выше.

| ID | Проверка / варианты | Ожидаемый результат | Статус | Автотест |
|---|---|---|---|---|
| HP-001 | min_price и max_price отдельно и совместно | 200; точный состав отелей и total по контролируемым данным | Passed | [test_hotels_price_filter](../tests/test_hotel_prices.py) |
| HP-002 | Равные границы и точные цены, включая 0.01 и 9999999999.99 | Границы включены; совпадающие номера учитываются | Passed | [test_hotels_price_filter](../tests/test_hotel_prices.py) |
| HP-003 | min_price=0 и max_price=0 | Ноль допустим как граница: min_price=0 включает отели с активными номерами; max_price=0 даёт пустую выборку | Passed | [test_hotels_price_filter](../tests/test_hotel_prices.py) |
| HP-004 | В одном отеле дешёвый номер ниже min, дорогой выше max; ни одного внутри диапазона | Отель исключён: нельзя удовлетворить две границы разными номерами | Passed | [test_hotels_price_filter](../tests/test_hotel_prices.py) |
| HP-005 | Дешёвые отключённые и архивные номера | Не влияют ни на включение в ценовой фильтр, ни на минимальную цену сортировки | Passed | [test_hotels_price_filter](../tests/test_hotel_prices.py), [test_hotels_price_sorting](../tests/test_hotel_prices.py) |
| HP-006 | Отели без номеров, только с отключёнными или только с архивными номерами | Исключены при ценовом фильтре | Passed | [test_hotels_price_filter](../tests/test_hotel_prices.py) |
| HP-007 | price и -price, в том числе 9000 и 10000 | Числовой порядок по минимальной цене, а не строковый | Passed | [test_hotels_price_sorting](../tests/test_hotel_prices.py) |
| HP-008 | Отели без активной цены при price и -price | Идут последними в обоих направлениях | Passed | [test_hotels_without_price_are_last](../tests/test_hotel_prices.py) |
| HP-009 | Равные минимальные цены и несколько отелей без цены | Внутри равенства UUID по возрастанию при обоих направлениях | Passed | [test_hotels_price_pagination](../tests/test_hotel_prices.py), [test_hotels_without_price_are_last](../tests/test_hotel_prices.py) |
| HP-010 | Диапазон 6000–8000 и сортировка price/-price; A: 1000/7000, B: 6500 | Попадают A и B; asc: A,B; desc: B,A. Для A сортировка использует 1000 | Passed | [test_hotels_filtered_price_sorting](../tests/test_hotel_prices.py) |
| HP-011 | Цена + город + рейтинг | Выполняются все условия; отель другого города с подходящими ценой и рейтингом исключён | Passed | [test_hotels_price_and_rating_filter](../tests/test_hotel_prices.py) |
| HP-012 | Пагинация при обоих направлениях сортировки по цене | Страницы соответствуют полному ожидаемому порядку, не пересекаются, total не меняется | Passed | [test_hotels_price_pagination](../tests/test_hotel_prices.py) |
| HP-013 | Отрицательные, слишком большие и нечисловые min_price/max_price | 422 VALIDATION_ERROR с путём query-параметра; единый формат и request ID | Passed | [test_hotels_invalid_price_parameters](../tests/test_hotel_prices.py) |
| HP-014 | min_price больше max_price | 422 INVALID_FILTER_RANGE; единый формат и request ID | Passed | [test_hotels_invalid_price_range](../tests/test_hotel_prices.py) |

<a id="hotels-checklist-ограничения-покрытия"></a>

### Ограничения покрытия

- Точный полный состав проверяется для уникального города; в глобальной выдаче без city проверяются ограничения рейтинга возвращённых записей и нижняя граница total, без предположений о числе записей на всём стенде.
- Бронирования не создаются: фильтр цены не проверяет свободные даты. Изменения номеров используются только как подготовка; самостоятельное полное покрытие ручек номеров не входит в этот блок.
- Не добавляются проверки JWT exp/iss/aud, конкурентных изменений и полное покрытие изменяющих операций.
- Результат относится к спокойному отдельному стенду: между чтениями одной выборки другие процессы не должны менять её данные.
- Несоответствия реализации требованиям фиксируются как дефекты; приложение и ожидаемые результаты не исправляются ради зелёного прогона.
