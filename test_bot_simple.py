"""Simple bot tester without ML dependencies - tests database operations only."""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import only database manager (no ML)
from src.database.db_manager import DatabaseManager


class SimpleBotTester:
    """Test bot database operations without running full bot."""

    def __init__(self):
        """Initialize tester."""
        print("🧪 Initializing Simple Bot Tester (Database Only)...")
        self.db = DatabaseManager("./data/bot_test.db")
        self.test_user_id = 99999  # Test user ID
        self.test_username = "test_user"
        self.test_first_name = "TestUser"

    def test_user_creation(self):
        """Test 1: Create user."""
        print(f"\n{'='*60}")
        print("TEST 1: User Creation")
        print(f"{'='*60}")

        user_id = self.db.create_user(
            self.test_user_id,
            self.test_username,
            self.test_first_name
        )

        if user_id:
            print(f"✅ User created with ID: {user_id}")
            return True
        else:
            print("❌ Failed to create user")
            return False

    def test_get_user(self):
        """Test 2: Get user."""
        print(f"\n{'='*60}")
        print("TEST 2: Get User")
        print(f"{'='*60}")

        user = self.db.get_user(self.test_user_id)

        if user:
            print("✅ User retrieved:")
            print(f"  - Telegram ID: {user['telegram_id']}")
            print(f"  - Username: {user['username']}")
            print(f"  - First name: {user['first_name']}")
            print(f"  - Messages/day: {user['messages_per_day']}")
            print(f"  - Active hours: {user['active_hours_start']} - {user['active_hours_end']}")
            print(f"  - Proactive enabled: {user['proactive_enabled']}")
            return True
        else:
            print("❌ User not found")
            return False

    def test_update_settings(self):
        """Test 3: Update user settings."""
        print(f"\n{'='*60}")
        print("TEST 3: Update Settings (Medium frequency)")
        print(f"{'='*60}")

        self.db.update_user_settings(
            self.test_user_id,
            messages_per_day=15,
            proactive_enabled=True
        )

        user = self.db.get_user(self.test_user_id)
        if user and user['messages_per_day'] == 15:
            print(f"✅ Settings updated:")
            print(f"  - Messages/day: {user['messages_per_day']}")
            print(f"  - Proactive: {user['proactive_enabled']}")
            return True
        else:
            print("❌ Settings not updated")
            return False

    def test_add_goals(self):
        """Test 4: Add goals."""
        print(f"\n{'='*60}")
        print("TEST 4: Add Goals")
        print(f"{'='*60}")

        goal1_id = self.db.add_goal(
            self.test_user_id,
            "Бегать каждое утро",
            description="30 минут бега",
            priority="high"
        )

        goal2_id = self.db.add_goal(
            self.test_user_id,
            "Читать 30 минут в день",
            description="Книги по саморазвитию",
            priority="medium"
        )

        if goal1_id and goal2_id:
            print(f"✅ Goals created:")
            print(f"  - Goal 1 ID: {goal1_id}")
            print(f"  - Goal 2 ID: {goal2_id}")
            return True
        else:
            print("❌ Failed to create goals")
            return False

    def test_get_goals(self):
        """Test 5: Get active goals."""
        print(f"\n{'='*60}")
        print("TEST 5: Get Active Goals")
        print(f"{'='*60}")

        goals = self.db.get_active_goals(self.test_user_id)

        if goals:
            print(f"✅ Found {len(goals)} active goals:")
            for g in goals:
                print(f"\n  Goal ID: {g['id']}")
                print(f"  - Title: {g['title']}")
                print(f"  - Description: {g['description']}")
                print(f"  - Priority: {g['priority']}")
                print(f"  - Status: {g['status']}")
                print(f"  - Progress: {g['progress']}%")
            return True
        else:
            print("❌ No goals found")
            return False

    def test_boost_mode(self):
        """Test 6: Enable boost mode."""
        print(f"\n{'='*60}")
        print("TEST 6: Enable Boost Mode (24h)")
        print(f"{'='*60}")

        self.db.enable_boost_mode(self.test_user_id, duration_hours=24)

        user = self.db.get_user(self.test_user_id)
        if user and user['boost_mode']:
            print(f"✅ Boost mode enabled:")
            print(f"  - Boost mode: {user['boost_mode']}")
            print(f"  - Expires at: {user['boost_expires_at']}")
            return True
        else:
            print("❌ Boost mode not enabled")
            return False

    def test_pause(self):
        """Test 7: Pause proactive messages."""
        print(f"\n{'='*60}")
        print("TEST 7: Pause Proactive Messages (3h)")
        print(f"{'='*60}")

        self.db.pause_proactive(self.test_user_id, duration_hours=3)

        user = self.db.get_user(self.test_user_id)
        if user and user['paused_until']:
            print(f"✅ Paused until: {user['paused_until']}")
            return True
        else:
            print("❌ Pause not set")
            return False

    def test_unpause(self):
        """Test 8: Unpause proactive messages."""
        print(f"\n{'='*60}")
        print("TEST 8: Unpause Proactive Messages")
        print(f"{'='*60}")

        self.db.unpause_proactive(self.test_user_id)

        user = self.db.get_user(self.test_user_id)
        if user and not user['paused_until']:
            print(f"✅ Unpaused successfully")
            return True
        else:
            print("❌ Still paused")
            return False

    def test_save_messages(self):
        """Test 9: Save messages."""
        print(f"\n{'='*60}")
        print("TEST 9: Save Messages (User & Assistant)")
        print(f"{'='*60}")

        msg1_id = self.db.save_message(
            self.test_user_id,
            'user',
            'Как мне начать бегать по утрам?',
            'reactive'
        )

        msg2_id = self.db.save_message(
            self.test_user_id,
            'assistant',
            'Отличный вопрос! Начни с малого - 5 минут каждое утро...',
            'reactive',
            tokens_used=150,
            rag_used=True
        )

        if msg1_id and msg2_id:
            print(f"✅ Messages saved:")
            print(f"  - User message ID: {msg1_id}")
            print(f"  - Assistant message ID: {msg2_id}")
            return True
        else:
            print("❌ Failed to save messages")
            return False

    def test_add_context(self):
        """Test 10: Add user context."""
        print(f"\n{'='*60}")
        print("TEST 10: Add User Context (Goal, Struggle, Win)")
        print(f"{'='*60}")

        ctx1_id = self.db.add_context(
            self.test_user_id,
            'goal',
            'Хочу пробежать марафон в этом году',
            priority='high'
        )

        ctx2_id = self.db.add_context(
            self.test_user_id,
            'struggle',
            'Не получается просыпаться рано'
        )

        ctx3_id = self.db.add_context(
            self.test_user_id,
            'win',
            'Сегодня пробежал 5км!'
        )

        if ctx1_id and ctx2_id and ctx3_id:
            print(f"✅ Context added:")
            print(f"  - Goal ID: {ctx1_id}")
            print(f"  - Struggle ID: {ctx2_id}")
            print(f"  - Win ID: {ctx3_id}")
            return True
        else:
            print("❌ Failed to add context")
            return False

    def test_personalities(self):
        """Test 11: Check personalities."""
        print(f"\n{'='*60}")
        print("TEST 11: Check Available Personalities")
        print(f"{'='*60}")

        conn = self.db._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM personalities WHERE is_active = 1")
            personalities = cursor.fetchall()

            if personalities:
                print(f"✅ Found {len(personalities)} personalities:")
                for p in personalities:
                    print(f"\n  {p['id']}. {p['display_name']} {p['avatar_emoji']}")
                    print(f"     Name: {p['name']}")
                    print(f"     Description: {p['description']}")
                    print(f"     Colors: {p['color_primary']} / {p['color_secondary']}")
                return True
            else:
                print("❌ No personalities found")
                return False
        finally:
            conn.close()

    def test_change_personality(self):
        """Test 12: Change active personality."""
        print(f"\n{'='*60}")
        print("TEST 12: Change Personality (to Tony Robbins)")
        print(f"{'='*60}")

        conn = self.db._get_connection()
        try:
            # Change to Tony Robbins (id=2)
            conn.execute(
                "UPDATE users SET active_personality_id = 2 WHERE telegram_id = ?",
                (self.test_user_id,)
            )
            conn.commit()

            user = self.db.get_user(self.test_user_id)
            if user and user['active_personality_id'] == 2:
                print(f"✅ Personality changed to ID: {user['active_personality_id']}")
                return True
            else:
                print("❌ Personality not changed")
                return False
        finally:
            conn.close()

    def run_full_test_suite(self):
        """Run all tests."""
        print("\n" + "="*60)
        print("🚀 STARTING SIMPLE BOT TEST SUITE (Database Only)")
        print("="*60)

        tests = [
            ("Test 1: User Creation", self.test_user_creation),
            ("Test 2: Get User", self.test_get_user),
            ("Test 3: Update Settings", self.test_update_settings),
            ("Test 4: Add Goals", self.test_add_goals),
            ("Test 5: Get Active Goals", self.test_get_goals),
            ("Test 6: Enable Boost Mode", self.test_boost_mode),
            ("Test 7: Pause Proactive", self.test_pause),
            ("Test 8: Unpause Proactive", self.test_unpause),
            ("Test 9: Save Messages", self.test_save_messages),
            ("Test 10: Add User Context", self.test_add_context),
            ("Test 11: Check Personalities", self.test_personalities),
            ("Test 12: Change Personality", self.test_change_personality),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"❌ EXCEPTION: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n\n{'='*60}")
        print("📊 TEST RESULTS")
        print(f"{'='*60}")
        print(f"✅ Passed: {passed}/{len(tests)}")
        print(f"❌ Failed: {failed}/{len(tests)}")
        print(f"📈 Success rate: {passed/len(tests)*100:.1f}%")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    tester = SimpleBotTester()
    tester.run_full_test_suite()
