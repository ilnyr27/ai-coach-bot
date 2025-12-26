"""Proactive message scheduler with intelligent distribution."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, time
from typing import Dict, List
import random
import logging

logger = logging.getLogger(__name__)


class ProactiveScheduler:
    """Intelligent scheduler for proactive messages."""

    MESSAGE_TYPES = {
        'morning': {'priority': 1, 'time': '09:00'},
        'midday': {'priority': 2, 'time': '14:00'},
        'evening': {'priority': 1, 'time': '20:00'},
        'checkin': {'priority': 5},
        'reminder': {'priority': 3},
        'motivation': {'priority': 4},
        'reflection': {'priority': 3},
    }

    def __init__(self, db_manager, message_generator, bot_app=None):
        """
        Initialize scheduler.

        Args:
            db_manager: DatabaseManager instance
            message_generator: ProactiveMessageGenerator instance
            bot_app: Telegram Application instance (optional, set later)
        """
        self.db = db_manager
        self.message_gen = message_generator
        self.bot_app = bot_app
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start the scheduler."""
        # Check for pending messages every minute
        self.scheduler.add_job(
            self.process_pending_messages,
            'cron',
            minute='*',  # Every minute
            id='process_pending'
        )

        # Schedule daily planning at midnight
        self.scheduler.add_job(
            self.schedule_daily_for_all_users,
            'cron',
            hour=0,
            minute=5,
            id='daily_planning'
        )

        self.scheduler.start()
        logger.info("✅ Proactive scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("🛑 Proactive scheduler stopped")

    async def schedule_daily_for_all_users(self):
        """Schedule messages for all active users for the day."""
        # Get all users with proactive enabled
        # This would require a new DB method
        logger.info("📅 Scheduling daily messages for all users...")

    def schedule_user_messages(self, telegram_id: int) -> int:
        """
        Schedule proactive messages for a user for the day.

        Args:
            telegram_id: User's telegram ID

        Returns:
            Number of messages scheduled
        """
        user = self.db.get_user(telegram_id)
        if not user:
            logger.warning(f"User {telegram_id} not found")
            return 0

        if not user['proactive_enabled']:
            logger.info(f"Proactive disabled for user {telegram_id}")
            return 0

        # Check if paused
        if user['paused_until']:
            paused_until = datetime.fromisoformat(user['paused_until'])
            if datetime.now() < paused_until:
                logger.info(f"User {telegram_id} paused until {paused_until}")
                return 0

        # Clear existing pending messages for today
        self.db.clear_pending_messages(telegram_id)

        # Calculate target message count
        target_count = user['messages_per_day']

        # Apply boost mode
        if user['boost_mode']:
            boost_expires = datetime.fromisoformat(user['boost_expires_at']) if user['boost_expires_at'] else None
            if boost_expires and datetime.now() < boost_expires:
                target_count *= 2
                logger.info(f"📈 Boost mode active for {telegram_id}: {target_count} messages")
            else:
                # Boost expired, disable it
                self.db.disable_boost_mode(telegram_id)

        # Get user context for intelligent scheduling
        goals = self.db.get_active_goals(telegram_id)
        context = self.db.get_recent_context(telegram_id, limit=10)

        # Parse active hours
        active_start = self._parse_time(user['active_hours_start'])
        active_end = self._parse_time(user['active_hours_end'])

        # Schedule fixed anchor messages
        scheduled_count = 0

        # Morning message
        morning_time = self._combine_date_time(datetime.now().date(), active_start)
        self.db.schedule_message(
            telegram_id,
            morning_time,
            'morning',
            priority=1,
            context_data={'goals': [g['title'] for g in goals[:3]]}
        )
        scheduled_count += 1

        # Midday message
        midday_time = self._combine_date_time(
            datetime.now().date(),
            time(14, 0)
        )
        if active_start.hour <= 14 <= active_end.hour:
            self.db.schedule_message(
                telegram_id,
                midday_time,
                'midday',
                priority=2
            )
            scheduled_count += 1

        # Evening message
        evening_time = self._combine_date_time(
            datetime.now().date(),
            time(20, 0)
        )
        if active_start.hour <= 20 <= active_end.hour:
            self.db.schedule_message(
                telegram_id,
                evening_time,
                'evening',
                priority=1
            )
            scheduled_count += 1

        # Distribute remaining messages intelligently
        remaining = target_count - scheduled_count

        if remaining > 0:
            scheduled_count += self._schedule_distributed_messages(
                telegram_id,
                remaining,
                active_start,
                active_end,
                goals
            )

        logger.info(f"✅ Scheduled {scheduled_count} messages for user {telegram_id}")
        return scheduled_count

    def _schedule_distributed_messages(
        self,
        telegram_id: int,
        count: int,
        start_time: time,
        end_time: time,
        goals: List[Dict]
    ) -> int:
        """Distribute messages throughout the day intelligently."""
        # Calculate time window in minutes
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        window_minutes = end_minutes - start_minutes

        if window_minutes <= 0:
            return 0

        # Calculate interval between messages
        interval_minutes = window_minutes // (count + 1)

        scheduled = 0
        for i in range(count):
            # Calculate base time
            offset_minutes = start_minutes + (interval_minutes * (i + 1))

            # Add randomness (+/- 15 minutes)
            offset_minutes += random.randint(-15, 15)

            # Ensure within bounds
            offset_minutes = max(start_minutes, min(end_minutes, offset_minutes))

            # Convert to time
            scheduled_hour = offset_minutes // 60
            scheduled_minute = offset_minutes % 60
            scheduled_time = self._combine_date_time(
                datetime.now().date(),
                time(scheduled_hour, scheduled_minute)
            )

            # Choose message type based on context
            msg_type = self._choose_message_type(scheduled_time, goals)

            # Schedule
            self.db.schedule_message(
                telegram_id,
                scheduled_time,
                msg_type,
                priority=self.MESSAGE_TYPES.get(msg_type, {}).get('priority', 5)
            )
            scheduled += 1

        return scheduled

    def _choose_message_type(self, scheduled_time: datetime, goals: List[Dict]) -> str:
        """Choose appropriate message type based on time and context."""
        hour = scheduled_time.hour

        # Morning hours (7-11) - planning/motivation
        if 7 <= hour <= 11:
            return random.choice(['checkin', 'motivation'])

        # Afternoon (11-17) - reminders/check-ins
        elif 11 <= hour <= 17:
            if goals and random.random() < 0.6:  # 60% chance if user has goals
                return 'reminder'
            return 'checkin'

        # Evening (17-22) - reflection
        elif 17 <= hour <= 22:
            return random.choice(['reflection', 'checkin'])

        # Default
        return 'checkin'

    async def process_pending_messages(self):
        """Check and process pending scheduled messages."""
        try:
            pending = self.db.get_pending_messages(telegram_id=None)  # Get all pending messages

            if not pending:
                return

            logger.info(f"📨 Processing {len(pending)} pending messages...")

            for msg in pending:
                try:
                    await self._send_scheduled_message(msg)
                except Exception as e:
                    logger.error(f"Error sending message {msg['id']}: {e}")

        except Exception as e:
            logger.error(f"Error processing pending messages: {e}")

    async def _send_scheduled_message(self, scheduled_msg: Dict):
        """Generate and send a scheduled message."""
        if not self.bot_app:
            logger.warning("Bot application not set, cannot send messages")
            return

        try:
            telegram_id = scheduled_msg['user_id']
            msg_type = scheduled_msg['message_type']

            # Get user to find telegram_id from user_id
            conn = self.db._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT telegram_id FROM users WHERE user_id = %s", (telegram_id,))
                    result = cur.fetchone()
                    if not result:
                        logger.error(f"User {telegram_id} not found")
                        return
                    telegram_id = result['telegram_id']
            finally:
                conn.close()

            # Generate proactive message
            logger.info(f"📨 Generating {msg_type} message for user {telegram_id}")
            message_text = await self.message_gen.generate_proactive_message(
                telegram_id=telegram_id,
                message_type=msg_type
            )

            # Send via bot
            await self.bot_app.bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )

            # Mark as sent
            self.db.mark_message_sent(scheduled_msg['id'])
            logger.info(f"✅ Sent {msg_type} message to {telegram_id}")

        except Exception as e:
            logger.error(f"❌ Error sending scheduled message {scheduled_msg['id']}: {e}")

    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object."""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        except:
            return time(7, 0)  # Default 7:00

    def _combine_date_time(self, date, time_obj: time) -> datetime:
        """Combine date and time into datetime."""
        return datetime.combine(date, time_obj)


if __name__ == "__main__":
    # Test scheduler
    import sys
    sys.path.insert(0, '../..')

    from src.database.db_manager import DatabaseManager

    print("🧪 Testing ProactiveScheduler\n")

    # Initialize
    db = DatabaseManager("./test_scheduler.db")

    # Create test user
    db.create_user(12345, "testuser", "Test")
    db.update_user_settings(12345, messages_per_day=10, proactive_enabled=True)

    # Add some goals
    db.add_goal(12345, "Бегать каждое утро", priority='high')
    db.add_goal(12345, "Читать 30 минут в день", priority='medium')

    # Create scheduler (without message generator for now)
    scheduler = ProactiveScheduler(db, None)

    # Schedule messages
    count = scheduler.schedule_user_messages(12345)
    print(f"\n✅ Scheduled {count} messages")

    # Check what was scheduled
    pending = db.get_pending_messages(datetime.now() + timedelta(days=1))
    print(f"\n📋 Pending messages ({len(pending)}):")
    for msg in pending[:5]:
        print(f"   {msg['scheduled_time']} - {msg['message_type']} (priority: {msg['priority']})")

    print("\n✅ Scheduler test completed!")
