from db import get_connection


def create_chat(title):
    connection = get_connection()

    cursor = connection.execute(
        "INSERT INTO chats (title) VALUES (?)",
        (title[:50],)
    )

    chat_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return chat_id


def save_message(chat_id, role, content):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO messages (chat_id, role, content)
        VALUES (?, ?, ?)
        """,
        (chat_id, role, content)
    )

    connection.commit()
    connection.close()


def get_chat_history(chat_id):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id
        """,
        (chat_id,)
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]