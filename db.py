from uuid import UUID

import psycopg


def move_booking_expiry_to_past(database_url, booking_id, user_id):
    with psycopg.connect(
        database_url,
        connect_timeout=5,
        options="-c lock_timeout=5000 -c statement_timeout=10000",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE bookings
                SET expires_at = clock_timestamp() - INTERVAL '1 minute'
                WHERE id = %s AND user_id = %s AND status = 'pending_payment'
                RETURNING expires_at
                """,
                (UUID(booking_id), UUID(user_id)),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Expected this user's pending booking in the configured test database")
            expires_at = row[0]
    return expires_at


def get_booking_payment_states(database_url, booking_id, user_id):
    """Read all payment IDs/statuses for this test user's booking, including non-pending rows."""
    with psycopg.connect(
        database_url,
        connect_timeout=5,
        options="-c default_transaction_read_only=on -c lock_timeout=5000 -c statement_timeout=10000",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.id, p.status
                FROM bookings AS b
                LEFT JOIN payments AS p ON p.booking_id = b.id
                WHERE b.id = %s AND b.user_id = %s
                ORDER BY p.id
                """,
                (UUID(booking_id), UUID(user_id)),
            )
            rows = cursor.fetchall()
            if not rows:
                raise ValueError("Expected this user's booking in the configured test database")
    return [{"id": str(payment_id), "status": status} for payment_id, status in rows if payment_id is not None]


def get_booking_payment_history(database_url, booking_id, user_id, payment_id):
    """Read transition histories only after verifying this payment belongs to this user's booking."""
    with psycopg.connect(
        database_url,
        connect_timeout=5,
        options="-c default_transaction_read_only=on -c lock_timeout=5000 -c statement_timeout=10000",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.id FROM payments AS p
                JOIN bookings AS b ON b.id = p.booking_id
                WHERE b.id = %s AND b.user_id = %s AND p.id = %s
                """,
                (UUID(booking_id), UUID(user_id), UUID(payment_id)),
            )
            if cursor.fetchone() is None:
                raise ValueError("Expected this user's booking and payment in the configured test database")
            cursor.execute(
                """
                SELECT from_status, to_status, actor_id
                FROM booking_status_history WHERE booking_id = %s
                ORDER BY created_at, id
                """,
                (UUID(booking_id),),
            )
            booking_history = cursor.fetchall()
            cursor.execute(
                """
                SELECT from_status, to_status, actor_id
                FROM payment_status_history WHERE payment_id = %s
                ORDER BY created_at, id
                """,
                (UUID(payment_id),),
            )
            payment_history = cursor.fetchall()
    return {
        "booking": [{"from_status": before, "to_status": after, "actor_id": str(actor) if actor else None}
                    for before, after, actor in booking_history],
        "payment": [{"from_status": before, "to_status": after, "actor_id": str(actor) if actor else None}
                    for before, after, actor in payment_history],
    }


def move_confirmed_booking_checkout_to_today(database_url, booking_id, user_id):
    """Move only this user's confirmed stay to UTC check-out day, preserving nights and price."""
    with psycopg.connect(
        database_url,
        connect_timeout=5,
        options="-c lock_timeout=5000 -c statement_timeout=10000",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE bookings
                SET check_in = (statement_timestamp() AT TIME ZONE 'UTC')::date - (check_out - check_in),
                    check_out = (statement_timestamp() AT TIME ZONE 'UTC')::date
                WHERE id = %s AND user_id = %s AND status = 'confirmed'
                RETURNING check_in, check_out
                """,
                (UUID(booking_id), UUID(user_id)),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Expected this user's confirmed booking in the configured test database")
    return {"check_in": row[0].isoformat(), "check_out": row[1].isoformat()}
