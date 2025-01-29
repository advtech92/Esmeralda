import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional


import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = "data/moments.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            # Drop tables if they exist (for development)
            conn.execute("DROP TABLE IF EXISTS incidents")
            conn.execute("DROP TABLE IF EXISTS incident_messages")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS funny_moments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_link TEXT NOT NULL,
                    description TEXT,
                    author_id INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    capture_mode TEXT NOT NULL,
                    capture_param TEXT,
                    start_time DATETIME,
                    end_time DATETIME
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS incident_messages (
                    incident_id TEXT,
                    message_id INTEGER,
                    author_id INTEGER,
                    content TEXT,
                    timestamp DATETIME,
                    PRIMARY KEY (incident_id, message_id),
                    FOREIGN KEY (incident_id) REFERENCES incidents(id)
                )
            """)
            conn.commit()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def add_incident(self, incident_id: str, reason: str, moderator_id: int, 
                    messages: List[Dict], capture_mode: str, capture_param: str,
                    start_time: datetime = None, end_time: datetime = None) -> bool:
        """Store an incident with related messages"""
        try:
            with self._get_connection() as conn:
                # Add incident record
                conn.execute("""
                    INSERT INTO incidents 
                    (id, reason, moderator_id, timestamp, capture_mode, capture_param, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    incident_id,
                    reason,
                    moderator_id,
                    datetime.now(),
                    capture_mode,
                    capture_param,
                    start_time,
                    end_time
                ))

                # Add incident messages
                for msg in messages:
                    conn.execute("""
                        INSERT INTO incident_messages
                        (incident_id, message_id, author_id, content, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        incident_id,
                        msg['id'],
                        msg['author_id'],
                        msg['content'],
                        msg['timestamp']
                    ))

                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to save incident: {str(e)}")
            return False

    def add_funny_moment(self, message_link: str, author_id: int, description: str = None) -> int:
        """Store a funny moment in database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO funny_moments 
                (message_link, description, author_id, timestamp)
                VALUES (?, ?, ?, ?)
            """, (message_link, description, author_id, datetime.now()))
            conn.commit()
            return cursor.lastrowid

    def get_incident(self, incident_id: str) -> Optional[Dict]:
        """Retrieve an incident with its messages"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get incident details
            cursor.execute("""
                SELECT * FROM incidents
                WHERE id = ?
            """, (incident_id,))
            incident = cursor.fetchone()

            if not incident:
                return None

            # Get related messages
            cursor.execute("""
                SELECT * FROM incident_messages
                WHERE incident_id = ?
                ORDER BY timestamp ASC
            """, (incident_id,))
            messages = cursor.fetchall()

            return {
                "details": dict(incident),
                "messages": [dict(msg) for msg in messages]
            }

    def get_recent_incidents(self, moderator_id: int, limit: int = 25):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM incidents
                WHERE moderator_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (moderator_id, limit))
            return [dict(row) for row in cursor.fetchall()]
