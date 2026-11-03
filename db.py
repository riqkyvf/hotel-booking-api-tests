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
