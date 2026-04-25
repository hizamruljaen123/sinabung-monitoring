import os
import mysql.connector
from datetime import datetime
from decimal import Decimal
from config import IMPORTANT_TABLES


def get_db_connection():
    """Create and return a MySQL connection using environment variables."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "database.asetpedia.online"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "asetpedia"),
            port=int(os.getenv("DB_PORT", "3306"))
        )
        return conn
    except Exception as e:
        print(f"DB Error: {e}")
        return None


def get_table_counts():
    """Return a dict of {table_name: row_count} for IMPORTANT_TABLES."""
    conn = get_db_connection()
    counts = {}
    if conn:
        cursor = conn.cursor()
        for table in IMPORTANT_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                result = cursor.fetchone()
                counts[table] = result[0] if result else 0
            except Exception:
                counts[table] = -1
        cursor.close()
        conn.close()
    else:
        for table in IMPORTANT_TABLES:
            counts[table] = -1
    return counts


def serialize_row(row):
    """Convert datetime/Decimal values in a row dict to JSON-safe types."""
    for key, val in row.items():
        if isinstance(val, datetime):
            row[key] = val.isoformat()
        elif isinstance(val, Decimal):
            row[key] = float(val)
    return row
