
import sqlite3

DATABASE = "students_ai.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
    """)

    connection.commit()
    connection.close()


def create_chat(title):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO chats (title) VALUES (?)",
        (title[:60],)
    )

    chat_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return chat_id


def save_message(chat_id, role, content):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content)
    )

    connection.commit()
    connection.close()


def get_chat_history(chat_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT role, content, created_at FROM messages WHERE chat_id = ? ORDER BY id",
        (chat_id,)
    )

    messages = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return messages
