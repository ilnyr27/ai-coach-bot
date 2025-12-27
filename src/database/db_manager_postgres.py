"""Database manager for PostgreSQL operations (Supabase)."""

import sys
import psycopg2
from psycopg2.extras import RealDictCursor
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
    """Manage PostgreSQL database for proactive bot."""

    def __init__(self, connection_string: str = None):
        """Initialize database manager."""
        self.connection_string = connection_string or os.getenv('DATABASE_URL')

        if not self.connection_string:
            raise ValueError("DATABASE_URL not set in environment")

        print(f"✅ Database manager initialized (PostgreSQL)")

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.connection_string, cursor_factory=RealDictCursor)

    # ==================== USER MANAGEMENT ====================

    def create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> int:
        """Create new user or return existing user_id."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Check if exists
                cur.execute(
                    "SELECT user_id FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                row = cur.fetchone()

                if row:
                    return row['user_id']

                # Insert new user
                cur.execute(
                    "INSERT INTO users (telegram_id, username, first_name) VALUES (%s, %s, %s) RETURNING user_id",
                    (telegram_id, username, first_name)
                )
                user_id = cur.fetchone()['user_id']
                conn.commit()
                return user_id
        finally:
            conn.close()

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram_id."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                row = cur.fetchone()
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
            updates.append("messages_per_day = %s")
            params.append(messages_per_day)

        if active_hours_start is not None:
            updates.append("active_hours_start = %s")
            params.append(active_hours_start)

        if active_hours_end is not None:
            updates.append("active_hours_end = %s")
            params.append(active_hours_end)

        if proactive_enabled is not None:
            updates.append("proactive_enabled = %s")
            params.append(proactive_enabled)

        if not updates:
            return

        params.append(telegram_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE telegram_id = %s"

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    def enable_boost_mode(self, telegram_id: int, duration_hours: int = 24):
        """Enable boost mode (2x frequency) for specified duration."""
        expires_at = datetime.now() + timedelta(hours=duration_hours)

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET boost_mode = true, boost_expires_at = %s WHERE telegram_id = %s",
                    (expires_at, telegram_id)
                )
            conn.commit()
        finally:
            conn.close()

    def disable_boost_mode(self, telegram_id: int):
        """Disable boost mode."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET boost_mode = false, boost_expires_at = NULL WHERE telegram_id = %s",
                    (telegram_id,)
                )
            conn.commit()
        finally:
            conn.close()

    def pause_proactive(self, telegram_id: int, duration_hours: int = 3):
        """Pause proactive messages for specified duration."""
        paused_until = datetime.now() + timedelta(hours=duration_hours)

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET paused_until = %s WHERE telegram_id = %s",
                    (paused_until, telegram_id)
                )
            conn.commit()
        finally:
            conn.close()

    def unpause_proactive(self, telegram_id: int):
        """Unpause proactive messages."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET paused_until = NULL WHERE telegram_id = %s",
                    (telegram_id,)
                )
            conn.commit()
        finally:
            conn.close()

    # ==================== GOALS ====================

    def add_goal(self, telegram_id: int, title: str, description: str = None, priority: str = 'medium') -> Optional[int]:
        """Add a new goal for user."""
        # Get user_id
        user = self.get_user(telegram_id)
        if not user:
            return None

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO goals (user_id, title, description, priority) VALUES (%s, %s, %s, %s) RETURNING id",
                    (user['user_id'], title, description, priority)
                )
                goal_id = cur.fetchone()['id']
            conn.commit()
            return goal_id
        finally:
            conn.close()

    def get_active_goals(self, telegram_id: int) -> List[Dict]:
        """Get all active goals for user."""
        user = self.get_user(telegram_id)
        if not user:
            return []

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM goals WHERE user_id = %s AND status = 'active' ORDER BY priority DESC, created_at DESC",
                    (user['user_id'],)
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update_goal_progress(self, goal_id: int, progress: int):
        """Update goal progress (0-100)."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE goals SET progress = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (progress, goal_id)
                )
            conn.commit()
        finally:
            conn.close()

    def delete_goal(self, goal_id: int):
        """Soft delete goal by setting status to 'deleted'."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE goals SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (goal_id,)
                )
            conn.commit()
        finally:
            conn.close()

    def complete_goal(self, goal_id: int):
        """Mark goal as completed."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE goals SET status = 'completed', progress = 100, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (goal_id,)
                )
            conn.commit()
        finally:
            conn.close()

    # ==================== CONTEXT ====================

    def add_context(self, telegram_id: int, context_type: str, content: str, priority: str = 'medium') -> Optional[int]:
        """Add user context (goal, struggle, win)."""
        user = self.get_user(telegram_id)
        if not user:
            return None

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_context (user_id, context_type, content, priority) VALUES (%s, %s, %s, %s) RETURNING id",
                    (user['user_id'], context_type, content, priority)
                )
                context_id = cur.fetchone()['id']
            conn.commit()
            return context_id
        finally:
            conn.close()

    def get_user_context(self, telegram_id: int, context_type: str = None, limit: int = 10) -> List[Dict]:
        """Get user context, optionally filtered by type."""
        user = self.get_user(telegram_id)
        if not user:
            return []

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if context_type:
                    cur.execute(
                        "SELECT * FROM user_context WHERE user_id = %s AND context_type = %s ORDER BY mentioned_at DESC LIMIT %s",
                        (user['user_id'], context_type, limit)
                    )
                else:
                    cur.execute(
                        "SELECT * FROM user_context WHERE user_id = %s ORDER BY mentioned_at DESC LIMIT %s",
                        (user['user_id'], limit)
                    )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_recent_context(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Get recent context for user (alias for get_user_context)."""
        return self.get_user_context(telegram_id, limit=limit)

    # ==================== MESSAGES ====================

    def save_message(
        self,
        telegram_id: int,
        role: str,
        content: str,
        message_type: str = 'reactive',
        tokens_used: int = 0,
        rag_used: bool = False
    ) -> Optional[int]:
        """Save message to history."""
        user = self.get_user(telegram_id)
        if not user:
            return None

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO messages (user_id, role, content, message_type, tokens_used, rag_used)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                    (user['user_id'], role, content, message_type, tokens_used, rag_used)
                )
                msg_id = cur.fetchone()['id']
            conn.commit()
            return msg_id
        finally:
            conn.close()

    def get_message_history(self, telegram_id: int, limit: int = 20) -> List[Dict]:
        """Get message history for user."""
        user = self.get_user(telegram_id)
        if not user:
            return []

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM messages WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                    (user['user_id'], limit)
                )
                return [dict(row) for row in cur.fetchall()]
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
    ) -> Optional[int]:
        """Schedule a proactive message."""
        user = self.get_user(telegram_id)
        if not user:
            return None

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO scheduled_messages (user_id, scheduled_time, message_type, priority, context_data)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (user['user_id'], scheduled_time, message_type, priority, json.dumps(context_data) if context_data else None)
                )
                sched_id = cur.fetchone()['id']
            conn.commit()
            return sched_id
        finally:
            conn.close()

    def get_pending_messages(self, telegram_id: int = None) -> List[Dict]:
        """Get pending scheduled messages."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if telegram_id:
                    user = self.get_user(telegram_id)
                    if not user:
                        return []
                    cur.execute(
                        """SELECT * FROM scheduled_messages
                           WHERE user_id = %s AND status = 'pending' AND scheduled_time <= CURRENT_TIMESTAMP
                           ORDER BY priority ASC, scheduled_time ASC""",
                        (user['user_id'],)
                    )
                else:
                    cur.execute(
                        """SELECT * FROM scheduled_messages
                           WHERE status = 'pending' AND scheduled_time <= CURRENT_TIMESTAMP
                           ORDER BY priority ASC, scheduled_time ASC"""
                    )
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def mark_message_sent(self, message_id: int):
        """Mark scheduled message as sent."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE scheduled_messages SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (message_id,)
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
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM scheduled_messages WHERE user_id = %s AND status = 'pending'",
                    (user['user_id'],)
                )
            conn.commit()
        finally:
            conn.close()

    # ==================== PERSONALITIES ====================

    def get_personality(self, personality_id: int) -> Optional[Dict]:
        """Get personality by ID."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM personalities WHERE id = %s",
                    (personality_id,)
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def get_all_personalities(self) -> List[Dict]:
        """Get all active personalities."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM personalities WHERE is_active = true ORDER BY id")
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update_user_personality(self, telegram_id: int, personality_id: int):
        """Update user's active personality."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET active_personality_id = %s WHERE telegram_id = %s",
                    (personality_id, telegram_id)
                )
            conn.commit()
        finally:
            conn.close()
