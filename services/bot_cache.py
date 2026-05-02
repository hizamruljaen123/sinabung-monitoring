import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'bot_history.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Table for tracking sent messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            message_id INTEGER,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_date DATE
        )
    ''')
    # Create index for faster deletion by date
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON sent_messages(sent_date)')
    conn.commit()
    conn.close()

def save_message(chat_id, message_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO sent_messages (chat_id, message_id, sent_date) VALUES (?, ?, ?)',
            (str(chat_id), message_id, date.today().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLite] Save error: {e}")

def get_today_messages(chat_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT message_id FROM sent_messages WHERE chat_id = ? AND sent_date = ?',
            (str(chat_id), date.today().isoformat())
        )
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"[SQLite] Get error: {e}")
        return []

def clear_today_cache(chat_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM sent_messages WHERE chat_id = ? AND sent_date = ?',
            (str(chat_id), date.today().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLite] Clear error: {e}")

def get_all_messages(chat_id):
    """Retrieve all message IDs for a specific chat, regardless of date."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT message_id FROM sent_messages WHERE chat_id = ?',
            (str(chat_id),)
        )
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"[SQLite] Get all error: {e}")
        return []

def clear_all_cache(chat_id):
    """Remove all records for a specific chat."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sent_messages WHERE chat_id = ?', (str(chat_id),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLite] Clear all error: {e}")

def get_full_history(limit=50):
    """Get recent activity for the dashboard."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, chat_id, message_id, sent_at, sent_date 
            FROM sent_messages 
            ORDER BY sent_at DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"[SQLite] History error: {e}")
        return []

# Initialize on import
init_db()
