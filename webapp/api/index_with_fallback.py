"""Flask app for Vercel - Telegram Mini App with PostgreSQL and fallback to mock."""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__, template_folder='../templates')
CORS(app)

# PostgreSQL connection - Direct connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:Pofudu92pofudu92@db.fpackkversmdotxrsscv.supabase.co:5432/postgres?sslmode=require&connect_timeout=5')

# Mock data for fallback
MOCK_PERSONALITIES = [
    {
        'id': 1, 'name': 'james_clear', 'display_name': 'Джеймс Клир',
        'description': 'Автор "Атомных привычек"',
        'avatar_emoji': '📚', 'color_primary': '#667eea', 'color_secondary': '#764ba2',
        'is_active': True
    },
    {
        'id': 2, 'name': 'tony_robbins', 'display_name': 'Тони Роббинс',
        'description': 'Мотивационный коуч',
        'avatar_emoji': '🔥', 'color_primary': '#ff6b6b', 'color_secondary': '#ee5a6f',
        'is_active': True
    },
    {
        'id': 3, 'name': 'andrew_huberman', 'display_name': 'Эндрю Хуберман',
        'description': 'Нейробиолог из Stanford',
        'avatar_emoji': '🧠', 'color_primary': '#4ecdc4', 'color_secondary': '#44a08d',
        'is_active': True
    },
    {
        'id': 4, 'name': 'naval_ravikant', 'display_name': 'Навал Равикант',
        'description': 'Предприниматель и философ',
        'avatar_emoji': '🧘', 'color_primary': '#95e1d3', 'color_secondary': '#38ada9',
        'is_active': True
    },
    {
        'id': 5, 'name': 'tim_ferriss', 'display_name': 'Тим Феррис',
        'description': 'Автор "4-часовой рабочей недели"',
        'avatar_emoji': '⚡', 'color_primary': '#f9ca24', 'color_secondary': '#f0932b',
        'is_active': True
    }
]

def get_db():
    """Get database connection with fallback."""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=5)
        # Test connection
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except Exception as e:
        print(f"⚠️ PostgreSQL unavailable (using mock data): {e}")
        return None

@app.route('/')
def index():
    return render_template('dashboard_v2.html')

@app.route('/api/personalities')
def get_personalities():
    conn = get_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM personalities WHERE is_active = true ORDER BY id")
                personalities = [dict(row) for row in cur.fetchall()]
            return jsonify({'personalities': personalities})
        finally:
            conn.close()
    else:
        # Fallback to mock data
        return jsonify({'personalities': MOCK_PERSONALITIES})

@app.route('/api/user/<int:telegram_id>/personality', methods=['POST'])
def update_personality(telegram_id):
    data = request.get_json()
    personality_id = data.get('personality_id')

    conn = get_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET active_personality_id = %s WHERE telegram_id = %s",
                    (personality_id, telegram_id)
                )
            conn.commit()
            return jsonify({'success': True, 'personality_id': personality_id})
        finally:
            conn.close()
    else:
        # Mock success
        return jsonify({'success': True, 'personality_id': personality_id, 'mock': True})

@app.route('/api/user/<int:telegram_id>')
def get_user_data(telegram_id):
    conn = get_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
                user_row = cur.fetchone()

                if not user_row:
                    cur.execute(
                        """INSERT INTO users (telegram_id, username, first_name)
                           VALUES (%s, %s, %s) RETURNING *""",
                        (telegram_id, f'user_{telegram_id}', 'User')
                    )
                    user_row = cur.fetchone()
                    conn.commit()

                user = dict(user_row)
                user_id = user['user_id']

                cur.execute("SELECT COUNT(*) as total FROM messages WHERE user_id = %s", (user_id,))
                total_messages = cur.fetchone()['total']

                cur.execute("SELECT COUNT(*) as total FROM goals WHERE user_id = %s AND status = 'active'", (user_id,))
                active_goals = cur.fetchone()['total']

                stats = {
                    'total_messages': total_messages,
                    'active_goals': active_goals,
                    'response_rate': 0.85
                }

            return jsonify({'user': user, 'stats': stats})
        finally:
            conn.close()
    else:
        # Mock user data
        return jsonify({
            'user': {
                'telegram_id': telegram_id,
                'active_personality_id': 1,
                'messages_per_day': 15,
                'proactive_enabled': True
            },
            'stats': {
                'total_messages': 0,
                'active_goals': 0,
                'response_rate': 0.85
            },
            'mock': True
        })

@app.route('/api/goals/<int:telegram_id>')
def get_goals(telegram_id):
    conn = get_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
                user_row = cur.fetchone()

                if not user_row:
                    return jsonify({'goals': []})

                user_id = user_row['user_id']

                cur.execute(
                    """SELECT * FROM goals WHERE user_id = %s
                       ORDER BY status ASC, priority DESC, created_at DESC""",
                    (user_id,)
                )
                goals = [dict(row) for row in cur.fetchall()]

            return jsonify({'goals': goals})
        finally:
            conn.close()
    else:
        # Mock goals
        return jsonify({'goals': [], 'mock': True})

@app.route('/api/messages/<int:telegram_id>')
def get_messages(telegram_id):
    limit = request.args.get('limit', 20, type=int)
    conn = get_db()

    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
                user_row = cur.fetchone()

                if not user_row:
                    return jsonify({'messages': []})

                user_id = user_row['user_id']

                cur.execute(
                    """SELECT * FROM messages WHERE user_id = %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, limit)
                )
                messages = [dict(row) for row in cur.fetchall()]

            return jsonify({'messages': messages})
        finally:
            conn.close()
    else:
        return jsonify({'messages': [], 'mock': True})

@app.route('/api/context/<int:telegram_id>')
def get_context(telegram_id):
    conn = get_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
                user_row = cur.fetchone()

                if not user_row:
                    return jsonify({'context': []})

                user_id = user_row['user_id']

                cur.execute(
                    """SELECT * FROM user_context WHERE user_id = %s
                       ORDER BY mentioned_at DESC LIMIT 50""",
                    (user_id,)
                )
                context = [dict(row) for row in cur.fetchall()]

            return jsonify({'context': context})
        finally:
            conn.close()
    else:
        return jsonify({'context': [], 'mock': True})

@app.route('/api/scheduled/<int:telegram_id>')
def get_scheduled(telegram_id):
    conn = get_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
                user_row = cur.fetchone()

                if not user_row:
                    return jsonify({'scheduled': []})

                user_id = user_row['user_id']

                cur.execute(
                    """SELECT * FROM scheduled_messages WHERE user_id = %s
                       ORDER BY scheduled_time ASC LIMIT 50""",
                    (user_id,)
                )
                scheduled = [dict(row) for row in cur.fetchall()]

            return jsonify({'scheduled': scheduled})
        finally:
            conn.close()
    else:
        return jsonify({'scheduled': [], 'mock': True})

# For local development
if __name__ == '__main__':
    print("🚀 Starting Flask with PostgreSQL fallback to mock data...")
    print("⚠️ If VPN is active, PostgreSQL may not be accessible")
    app.run(debug=True, port=5000)
