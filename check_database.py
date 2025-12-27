"""Check Railway PostgreSQL data for debugging Dashboard."""
# -*- coding: utf-8 -*-

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATABASE_URL = "postgresql://postgres:AFdioPMdrLkwGXSULdooIYGIJhNICvBo@tramway.proxy.rlwy.net:20664/railway"

def check_database():
    """Check database contents."""
    print("Connecting to Railway PostgreSQL...")

    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Check users
        print("\nUSERS:")
        cur.execute("SELECT telegram_id, username, first_name, active_personality_id FROM users")
        users = cur.fetchall()
        if users:
            for user in users:
                print(f"  - Telegram ID: {user['telegram_id']}, Name: {user['first_name']}, Personality: {user['active_personality_id']}")
        else:
            print("  No users found!")

        # Check goals for each user
        print("\nGOALS:")
        for user in users:
            cur.execute(
                "SELECT title, progress, status, priority, created_at FROM goals WHERE user_id = (SELECT user_id FROM users WHERE telegram_id = %s)",
                (user['telegram_id'],)
            )
            goals = cur.fetchall()
            print(f"  User {user['telegram_id']} ({user['first_name']}):")
            if goals:
                for goal in goals:
                    print(f"    - {goal['title']} | Progress: {goal['progress']}% | Status: {goal['status']}")
            else:
                print(f"    No goals")

        # Check personalities
        print("\nPERSONALITIES:")
        cur.execute("SELECT id, display_name, avatar_emoji FROM personalities WHERE is_active = true")
        personalities = cur.fetchall()
        for p in personalities:
            print(f"  - {p['id']}. {p['display_name']}")

        # Check messages count
        print("\nMESSAGES:")
        for user in users:
            cur.execute(
                "SELECT COUNT(*) as count FROM messages WHERE user_id = (SELECT user_id FROM users WHERE telegram_id = %s)",
                (user['telegram_id'],)
            )
            count = cur.fetchone()['count']
            print(f"  User {user['telegram_id']}: {count} messages")

        # Check user_context
        print("\nUSER CONTEXT:")
        for user in users:
            cur.execute(
                "SELECT context_type, content FROM user_context WHERE user_id = (SELECT user_id FROM users WHERE telegram_id = %s) ORDER BY mentioned_at DESC LIMIT 5",
                (user['telegram_id'],)
            )
            contexts = cur.fetchall()
            print(f"  User {user['telegram_id']} ({user['first_name']}):")
            if contexts:
                for ctx in contexts:
                    print(f"    - [{ctx['context_type']}] {ctx['content'][:50]}...")
            else:
                print(f"    No context data")

        cur.close()
        conn.close()

        print("\nDatabase check complete!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database()
