"""Create PostgreSQL tables in Railway database."""

import psycopg2
import sys

# Railway PostgreSQL connection string
DATABASE_URL = "postgresql://postgres:AFdioPMdrLkwGXSULdooIYGIJhNICvBo@tramway.proxy.rlwy.net:20664/railway"

def create_tables():
    """Create all tables in Railway PostgreSQL."""

    print("🔗 Connecting to Railway PostgreSQL...")

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("✅ Connected successfully!")
        print("\n📦 Creating tables...")

        # Read SQL schema
        with open('railway_init.sql', 'r', encoding='utf-8') as f:
            sql_schema = f.read()

        # Execute schema
        cur.execute(sql_schema)
        conn.commit()

        print("✅ Tables created successfully!")

        # Verify tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cur.fetchall()

        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   ✅ {table[0]}")

        # Check personalities data
        cur.execute("SELECT COUNT(*) FROM personalities;")
        personality_count = cur.fetchone()[0]
        print(f"\n🤖 Inserted {personality_count} personalities")

        cur.close()
        conn.close()

        print("\n🎉 Database initialization complete!")
        print("\nYour bot can now:")
        print("  ✅ Save goals to PostgreSQL")
        print("  ✅ Store message history")
        print("  ✅ Schedule proactive messages")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_tables()
