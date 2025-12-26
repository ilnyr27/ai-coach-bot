"""Migrate data from SQLite to PostgreSQL."""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def migrate_sqlite_to_postgres(sqlite_path, postgres_url):
    """Migrate all data from SQLite to PostgreSQL."""

    print("🔄 Starting migration from SQLite to PostgreSQL...")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(postgres_url)
    pg_cur = pg_conn.cursor()

    try:
        # Tables to migrate (in order due to foreign keys)
        tables = [
            'personalities',
            'users',
            'user_context',
            'goals',
            'messages',
            'scheduled_messages',
            'important_dates',
            'activity_log'
        ]

        for table in tables:
            print(f"\n📦 Migrating table: {table}")

            # Get data from SQLite
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()

            if not rows:
                print(f"   ⚠️  No data in {table}")
                continue

            # Get column names
            columns = [desc[0] for desc in sqlite_cur.description]

            # Skip auto-increment ID for PostgreSQL (let it auto-generate)
            if 'id' in columns and table != 'users':
                columns_no_id = [col for col in columns if col != 'id']
                data = [[row[col] for col in columns_no_id] for row in rows]

                # Insert into PostgreSQL
                if data:
                    cols_str = ', '.join(columns_no_id)
                    placeholders = ', '.join(['%s'] * len(columns_no_id))
                    query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

                    for row_data in data:
                        pg_cur.execute(query, row_data)

            elif table == 'users':
                # For users table, handle user_id specially
                columns_no_id = [col for col in columns if col != 'user_id']
                data = [[row[col] for col in columns_no_id] for row in rows]

                if data:
                    cols_str = ', '.join(columns_no_id)
                    placeholders = ', '.join(['%s'] * len(columns_no_id))
                    query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT (telegram_id) DO NOTHING"

                    for row_data in data:
                        pg_cur.execute(query, row_data)

            else:
                # Insert with all columns
                data = [[row[col] for col in columns] for row in rows]

                if data:
                    cols_str = ', '.join(columns)
                    placeholders = ', '.join(['%s'] * len(columns))
                    query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

                    for row_data in data:
                        pg_cur.execute(query, row_data)

            pg_conn.commit()
            print(f"   ✅ Migrated {len(rows)} rows")

        # Reset sequences for auto-increment
        print("\n🔧 Resetting PostgreSQL sequences...")
        for table in tables:
            if table == 'users':
                pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('users', 'user_id'), (SELECT MAX(user_id) FROM users));")
            else:
                pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1));")
        pg_conn.commit()

        print("\n✅ Migration completed successfully!")

        # Show stats
        print("\n📊 Migration statistics:")
        for table in tables:
            pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = pg_cur.fetchone()[0]
            print(f"   {table}: {count} rows")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        pg_conn.rollback()
        raise

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    # Configuration
    SQLITE_PATH = "./data/bot.db"

    # Get PostgreSQL URL from environment variable
    # Set DATABASE_URL in your environment before running this script
    POSTGRES_URL = os.getenv('DATABASE_URL')

    if not POSTGRES_URL:
        print("❌ DATABASE_URL environment variable not set!")
        print("   Set it with: export DATABASE_URL='postgresql://...'")
        sys.exit(1)

    if not os.path.exists(SQLITE_PATH):
        print(f"❌ SQLite database not found at: {SQLITE_PATH}")
        sys.exit(1)

    print(f"📂 SQLite database: {SQLITE_PATH}")
    print(f"🔗 PostgreSQL: {POSTGRES_URL[:50]}...")

    confirm = input("\n⚠️  This will migrate all data to PostgreSQL. Continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Migration cancelled.")
        sys.exit(0)

    migrate_sqlite_to_postgres(SQLITE_PATH, POSTGRES_URL)
