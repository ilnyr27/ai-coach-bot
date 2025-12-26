"""Database manager for SQLite operations."""

import sys
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class DatabaseManager:
    """Manage SQLite database for proactive bot."""

    def __init__(self, db_path: str = "./data/bot.db"):
        """Initialize database manager."""
        self.db_path = db_path

        # Create directory if doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Create tables if they don't exist."""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()

        conn = self._get_connection()
        try:
            conn.executescript(schema)
            conn.commit()
            print(f"✅ Database initialized at: {self.db_path}")
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    # ==================== USER MANAGEMENT ====================

    def create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> int:
        """Create new user or return existing user_id."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT user_id FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = cursor.fetchone()

            if row:
                return row['user_id']

            cursor = conn.execute(
                "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                (telegram_id, username, first_name)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram_id."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_user_settings(
        self,
        telegram_id: int,
        messages_per_day: int = None,
        active_hours_start: str = None,
        active_hours_end: str = None,
        proactive_enabled: bool = None
    ):
        """Update user proactive settings."""
        updates = []
        params = []

        if messages_per_day is not None:
            updates.append("messages_per_day = ?")
            params.append(messages_per_day)

        if active_hours_start is not None:
            updates.append("active_hours_start = ?")
            params.append(active_hours_start)

        if active_hours_end is not None:
            updates.append("active_hours_end = ?")
            params.append(active_hours_end)

        if proactive_enabled is not None:
            updates.append("proactive_enabled = ?")
            params.append(1 if proactive_enabled else 0)

        if not updates:
            return

        params.append(telegram_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE telegram_id = ?"

        conn = self._get_connection()
        try:
            conn.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    def enable_boost_mode(self, telegram_id: int, duration_hours: int = 24):
        """Enable boost mode (2x frequency) for specified duration."""
        expires_at = datetime.now() + timedelta(hours=duration_hours)

        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE users SET boost_mode = 1, boost_expires_at = ? WHERE telegram_id = ?",
                (expires_at, telegram_id)
            )
            conn.commit()
        finally:
            conn.close()

    def disable_boost_mode(self, telegram_id: int):
        """Disable boost mode."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE users SET boost_mode = 0, boost_expires_at = NULL WHERE telegram_id = ?",
                (telegram_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def pause_proactive(self, telegram_id: int, duration_hours: int):
        """Pause proactive messages for specified duration."""
        paused_until = datetime.now() + timedelta(hours=duration_hours)

        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE users SET paused_until = ? WHERE telegram_id = ?",
                (paused_until, telegram_id)
            )
            conn.commit()
        finally:
            conn.close()

    def unpause_proactive(self, telegram_id: int):
        """Unpause proactive messages."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE users SET paused_until = NULL WHERE telegram_id = ?",
                (telegram_id,)
            )
            conn.commit()
        finally:
            conn.close()

    # ==================== GOALS ====================

    def add_goal(self, telegram_id: int, title: str, description: str = None, priority: str = 'medium') -> int:
        """Add new goal for user."""
        user = self.get_user(telegram_id)
        if not user:
            return None

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO goals (user_id, title, description, priority) VALUES (?, ?, ?, ?)",
                (user['user_id'], title, description, priority)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_active_goals(self, telegram_id: int) -> List[Dict]:
        """Get all active goals for user."""
        user = self.get_user(telegram_id)
        if not user:
            return []

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM goals WHERE user_id = ? AND status = 'active' ORDER BY priority DESC, created_at DESC",
                (user['user_id'],)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_goal_progress(self, goal_id: int, progress: int):
        """Update goal progress (0-100)."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE goals SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (progress, goal_id)
            )
            conn.commit()
        finally:
            conn.close()

    def complete_goal(self, goal_id: int):
        """Mark goal as completed."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE goals SET status = 'completed', progress = 100, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (goal_id,)
            )
            conn.commit()
        finally:
            conn.close()

    # ==================== CONTEXT ====================

    def add_context(self, telegram_id: int, context_type: str, content: str, priority: str = 'medium'):
        """Add context item (goal, struggle, win, important_date)."""
        user = self.get_user(telegram_id)
        if not user:
            return

        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT INTO user_context (user_id, context_type, content, priority) VALUES (?, ?, ?, ?)",
                (user['user_id'], context_type, content, priority)
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_context(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Get recent context for user."""
        user = self.get_user(telegram_id)
        if not user:
            return []

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM user_context WHERE user_id = ? ORDER BY mentioned_at DESC LIMIT ?",
                (user['user_id'], limit)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== MESSAGES ====================

    def save_message(
        self,
        telegram_id: int,
        role: str,
        content: str,
        message_type: str = 'reactive',
        tokens_used: int = 0,
        rag_used: bool = False
    ) -> int:
        """Save message to history."""
        user = self.get_user(telegram_id)
        if not user:
            return None

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """INSERT INTO messages
                (user_id, role, content, message_type, tokens_used, rag_used)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (user['user_id'], role, content, message_type, tokens_used, 1 if rag_used else 0)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_recent_messages(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Get recent messages for context."""
        user = self.get_user(telegram_id)
        if not user:
            return []

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user['user_id'], limit)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== SCHEDULED MESSAGES ====================

    def schedule_message(
        self,
        telegram_id: int,
        scheduled_time: datetime,
        message_type: str,
        priority: int = 5,
        context_data: Dict = None
    ) -> int:
        """Schedule a proactive message."""
        user = self.get_user(telegram_id)
        if not user:
            return None

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """INSERT INTO scheduled_messages
                (user_id, scheduled_time, message_type, priority, context_data)
                VALUES (?, ?, ?, ?, ?)""",
                (user['user_id'], scheduled_time, message_type, priority, json.dumps(context_data) if context_data else None)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_pending_messages(self, before_time: datetime = None) -> List[Dict]:
        """Get pending scheduled messages."""
        if before_time is None:
            before_time = datetime.now()

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT sm.*, u.telegram_id
                FROM scheduled_messages sm
                JOIN users u ON sm.user_id = u.user_id
                WHERE sm.status = 'pending' AND sm.scheduled_time <= ?
                ORDER BY sm.priority ASC, sm.scheduled_time ASC""",
                (before_time,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def mark_message_sent(self, message_id: int):
        """Mark scheduled message as sent."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE scheduled_messages SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (message_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def mark_message_failed(self, message_id: int, error: str):
        """Mark scheduled message as failed."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE scheduled_messages SET status = 'failed', error_message = ? WHERE id = ?",
                (error, message_id)
            )
            conn.commit()
        finally:
            conn.close()

    def clear_pending_messages(self, telegram_id: int):
        """Clear all pending messages for user."""
        user = self.get_user(telegram_id)
        if not user:
            return

        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE scheduled_messages SET status = 'cancelled' WHERE user_id = ? AND status = 'pending'",
                (user['user_id'],)
            )
            conn.commit()
        finally:
            conn.close()

    # ==================== STATS ====================

    def get_user_stats(self, telegram_id: int) -> Dict:
        """Get user statistics."""
        user = self.get_user(telegram_id)
        if not user:
            return {}

        conn = self._get_connection()
        try:
            # Total messages
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE user_id = ?",
                (user['user_id'],)
            )
            total_messages = cursor.fetchone()['count']

            # Active goals
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM goals WHERE user_id = ? AND status = 'active'",
                (user['user_id'],)
            )
            active_goals = cursor.fetchone()['count']

            # Response rate (last 20 proactive messages)
            cursor = conn.execute(
                """SELECT COUNT(*) as replied
                FROM messages
                WHERE user_id = ? AND message_type LIKE 'proactive_%' AND user_replied = 1
                LIMIT 20""",
                (user['user_id'],)
            )
            replied = cursor.fetchone()['replied']

            return {
                'total_messages': total_messages,
                'active_goals': active_goals,
                'response_rate': replied / 20.0 if total_messages >= 20 else 1.0
            }
        finally:
            conn.close()


if __name__ == "__main__":
    # Test database
    print("🧪 Testing DatabaseManager\n")

    db = DatabaseManager("./test_bot.db")

    # Create test user
    user_id = db.create_user(telegram_id=12345, username="testuser", first_name="Test")
    print(f"✅ Created user: {user_id}")

    # Update settings
    db.update_user_settings(12345, messages_per_day=20, proactive_enabled=True)
    print("✅ Updated settings")

    # Add goal
    goal_id = db.add_goal(12345, "Бегать каждое утро", priority='high')
    print(f"✅ Added goal: {goal_id}")

    # Get user
    user = db.get_user(12345)
    print(f"\n📊 User data:")
    print(f"   Messages per day: {user['messages_per_day']}")
    print(f"   Proactive enabled: {user['proactive_enabled']}")

    # Get goals
    goals = db.get_active_goals(12345)
    print(f"\n🎯 Goals: {len(goals)}")
    for goal in goals:
        print(f"   - {goal['title']} (priority: {goal['priority']})")

    print("\n✅ Database test completed!")
