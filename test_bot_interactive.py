"""Interactive bot tester - simulate user interactions with the bot."""

import os
import sys
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Load environment
load_dotenv()

# Import bot
from src.bot.proactive_bot import ProactiveJamesClearBot


class BotTester:
    """Test bot commands interactively."""

    def __init__(self):
        """Initialize tester."""
        print("🧪 Initializing Bot Tester...")
        self.bot = ProactiveJamesClearBot()
        self.test_user_id = 12345  # Test user ID
        self.test_username = "test_user"
        self.test_first_name = "Test"

    async def simulate_command(self, command: str, args: list = None):
        """Simulate a command from user."""
        print(f"\n{'='*60}")
        print(f"📤 Simulating: /{command} {' '.join(args) if args else ''}")
        print(f"{'='*60}")

        # Create mock update
        class MockMessage:
            def __init__(self, text, user_id, username, first_name):
                self.text = text
                self.chat = type('obj', (object,), {'id': user_id, 'send_action': self._send_action})
                self.from_user = type('obj', (object,), {
                    'id': user_id,
                    'username': username,
                    'first_name': first_name
                })
                self.effective_user = self.from_user
                self._replies = []

            async def _send_action(self, action):
                pass

            async def reply_text(self, text, **kwargs):
                print(f"\n📥 BOT RESPONSE:")
                print(f"{'-'*60}")
                print(text)
                print(f"{'-'*60}")
                self._replies.append(text)
                return self

        class MockUpdate:
            def __init__(self, message):
                self.message = message
                self.effective_user = message.from_user
                self.callback_query = None

        # Create mock context
        class MockContext:
            def __init__(self, args):
                self.args = args or []

        message = MockMessage(
            f"/{command}",
            self.test_user_id,
            self.test_username,
            self.test_first_name
        )
        update = MockUpdate(message)
        context = MockContext(args)

        # Call appropriate handler
        try:
            if command == "start":
                await self.bot.start_command(update, context)
            elif command == "dashboard":
                await self.bot.dashboard_command(update, context)
            elif command == "setup":
                await self.bot.setup_command(update, context)
            elif command == "goal":
                await self.bot.goal_command(update, context)
            elif command == "boost":
                await self.bot.boost_command(update, context)
            elif command == "pause":
                await self.bot.pause_command(update, context)
            elif command == "unpause":
                await self.bot.unpause_command(update, context)
            elif command == "settings":
                await self.bot.settings_command(update, context)
            else:
                print(f"❌ Unknown command: {command}")

            return True
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def simulate_button_click(self, callback_data: str):
        """Simulate clicking an inline button."""
        print(f"\n{'='*60}")
        print(f"🖱️  Simulating button click: {callback_data}")
        print(f"{'='*60}")

        class MockCallbackQuery:
            def __init__(self, data, user_id, username, first_name):
                self.data = data
                self.from_user = type('obj', (object,), {
                    'id': user_id,
                    'username': username,
                    'first_name': first_name
                })

            async def answer(self):
                pass

            async def edit_message_text(self, text, **kwargs):
                print(f"\n📥 BOT RESPONSE (edited):")
                print(f"{'-'*60}")
                print(text)
                print(f"{'-'*60}")

        class MockUpdate:
            def __init__(self, query):
                self.callback_query = query
                self.effective_user = query.from_user

        query = MockCallbackQuery(
            callback_data,
            self.test_user_id,
            self.test_username,
            self.test_first_name
        )
        update = MockUpdate(query)
        context = type('obj', (object,), {'args': []})

        try:
            await self.bot.frequency_callback(update, context)
            return True
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def check_database(self):
        """Check database state."""
        print(f"\n{'='*60}")
        print("🗄️  DATABASE STATE")
        print(f"{'='*60}")

        # Check user
        user = self.bot.db.get_user(self.test_user_id)
        if user:
            print(f"\n✅ User exists:")
            print(f"  - Telegram ID: {user['telegram_id']}")
            print(f"  - Username: {user['username']}")
            print(f"  - Messages/day: {user['messages_per_day']}")
            print(f"  - Proactive enabled: {user['proactive_enabled']}")
            print(f"  - Boost mode: {user['boost_mode']}")
        else:
            print("❌ User not found in database")

        # Check goals
        goals = self.bot.db.get_active_goals(self.test_user_id)
        if goals:
            print(f"\n✅ Active goals ({len(goals)}):")
            for g in goals:
                print(f"  - [{g['priority']}] {g['title']}")
        else:
            print("\n📝 No active goals")

    async def run_test_suite(self):
        """Run full test suite."""
        print("\n" + "="*60)
        print("🚀 STARTING BOT TEST SUITE")
        print("="*60)

        tests = [
            ("1. Test /start command",
             lambda: self.simulate_command("start")),

            ("2. Check database after /start",
             lambda: self.check_database()),

            ("3. Test /setup command",
             lambda: self.simulate_command("setup")),

            ("4. Simulate clicking 'Medium' button",
             lambda: self.simulate_button_click("freq_medium")),

            ("5. Test /goal command",
             lambda: self.simulate_command("goal", ["Бегать", "каждое", "утро"])),

            ("6. Test /goal command (2nd goal)",
             lambda: self.simulate_command("goal", ["Читать", "30", "минут"])),

            ("7. Test /settings command",
             lambda: self.simulate_command("settings")),

            ("8. Check database after goals",
             lambda: self.check_database()),

            ("9. Test /boost command",
             lambda: self.simulate_command("boost")),

            ("10. Test /pause command",
             lambda: self.simulate_command("pause", ["2ч"])),

            ("11. Test /unpause command",
             lambda: self.simulate_command("unpause")),

            ("12. Test /dashboard command",
             lambda: self.simulate_command("dashboard")),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"▶️  {test_name}")
            print(f"{'='*60}")

            try:
                result = await test_func()
                if result or result is None:
                    passed += 1
                    print(f"\n✅ PASSED")
                else:
                    failed += 1
                    print(f"\n❌ FAILED")
            except Exception as e:
                failed += 1
                print(f"\n❌ FAILED with exception: {e}")

            # Wait a bit between tests
            await asyncio.sleep(0.5)

        print(f"\n\n{'='*60}")
        print("📊 TEST RESULTS")
        print(f"{'='*60}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success rate: {passed/(passed+failed)*100:.1f}%")
        print(f"{'='*60}\n")


async def main():
    """Main entry point."""
    tester = BotTester()
    await tester.run_test_suite()


if __name__ == "__main__":
    asyncio.run(main())
