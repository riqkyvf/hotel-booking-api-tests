# Бизнес-правила

Краткая модель стоимости и состояний помогает читать тесты. Полный контракт: [требования API](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md).

## Даты и суммы

Даты заезда и выезда относятся к UTC. Номер резервируется на интервал `[check_in, check_out)`. [Ограничения дат и гостей](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-04-бронирования) · [Ограничения цены](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-03-каталог)

`nights = (check_out - check_in).days`

`total_price = Decimal(price_per_night) * nights`

Стоимость хранится как снимок. Нет скидок, налоговых надбавок, доплат за гостей и конвертации валюты. Денежные значения JSON возвращаются десятичными строками, например `"3000.00"`.

## Доступность

Доступность зависит от состояния номера, вместимости и отсутствия пересечений. API проверяет причины в порядке `ROOM_DISABLED` → `CAPACITY_EXCEEDED` → `ROOM_NOT_AVAILABLE`. Запрос доступности не резервирует даты. [Контракт запроса](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/api-specification.md#номера)

## Переходы бронирования

| Из | В | Условие | Блокирует номер после перехода |
|---|---|---|---|
| отсутствует | pending_payment | Создание | Да |
| pending_payment | confirmed | Успех оплаты до срока | Да |
| pending_payment | expired | now >= expires_at | Нет |
| pending_payment | cancelled | Отмена до даты заезда | Нет |
| confirmed | cancelled | Отмена до даты заезда и полный возврат | Нет |
| confirmed | completed | UTC-дата >= check_out | Нет |

`cancelled`, `expired`, `completed` — конечные. Повтор отмены возвращает `200` для брони в состоянии `cancelled`. [Правила отмены](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-08-отмена)

## Переходы платежа

| Из | В | Условие |
|---|---|---|
| отсутствует | pending | Создание операции для ожидающей оплаты брони |
| pending | succeeded | Успешная симуляция |
| pending | failed | Отклонённая симуляция |
| pending | cancelled | Истечение или отмена брони |
| succeeded | refunded | Отмена оплаченной брони до заезда |

`failed`, `cancelled`, `refunded` — конечные состояния платежа. После отказа можно создать новый платёж до истечения удержания. [Правила платежей и коды отказов](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-07-тестовые-платежи)

[Правила деактивации](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-02-деактивация), [истечения](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-05-точное-истечение) и [конкуренции](https://github.com/riqkyvf/hotel-booking-api/blob/0d8396f38c8a7b727648585e33b3d34fe54652ab/docs/requirements.md#fr-09-конкуренция) определяют, когда приложение применяет переходы.
