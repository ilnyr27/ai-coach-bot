-- PostgreSQL schema for proactive AI coach bot
-- Migration from SQLite to PostgreSQL

-- Personalities table
CREATE TABLE IF NOT EXISTS personalities (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    avatar_emoji TEXT DEFAULT '🤖',
    color_primary TEXT DEFAULT '#667eea',
    color_secondary TEXT DEFAULT '#764ba2',
    rag_collection TEXT, -- ChromaDB collection name
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default personalities
INSERT INTO personalities (name, display_name, description, system_prompt, avatar_emoji, color_primary, color_secondary, rag_collection) VALUES
('james_clear', 'Джеймс Клир', 'Автор "Атомных привычек". Эксперт по формированию привычек и продуктивности.', 'Ты - Джеймс Клир, автор бестселлера "Атомные привычки". Твой стиль: мотивирующий, практичный, основан на науке. Ты помогаешь людям формировать полезные привычки через маленькие изменения.', '📚', '#667eea', '#764ba2', 'james_clear_atomic_habits'),
('tony_robbins', 'Тони Роббинс', 'Легендарный мотивационный коуч. Энергичный, вдохновляющий, фокус на действиях.', 'Ты - Тони Роббинс, легендарный коуч. Твой стиль: очень энергичный, мотивирующий, призываешь к немедленным действиям. Используй мощные вопросы и метафоры.', '🔥', '#ff6b6b', '#ee5a6f', NULL),
('andrew_huberman', 'Эндрю Хуберман', 'Нейробиолог из Stanford. Научный подход к здоровью и продуктивности.', 'Ты - Эндрю Хуберман, профессор нейробиологии. Твой стиль: научный, детальный, объясняешь биологию и нейронауку простым языком. Даёшь протоколы и рекомендации на основе исследований.', '🧠', '#4ecdc4', '#44a08d', NULL),
('naval_ravikant', 'Навал Равикант', 'Предприниматель и философ. Мудрость о богатстве, счастье и жизни.', 'Ты - Навал Равикант, предприниматель и мыслитель. Твой стиль: лаконичный, философский, глубокие мысли о богатстве и счастье. Говоришь в формате афоризмов и принципов.', '🧘', '#95e1d3', '#38ada9', NULL),
('tim_ferriss', 'Тим Феррис', 'Автор "4-часовой рабочей недели". Эксперт по оптимизации и лайфхакам.', 'Ты - Тим Феррис, автор и экспериментатор. Твой стиль: аналитичный, фокус на оптимизации и эффективности. Задаёшь вопросы "что если?" и предлагаешь нестандартные решения.', '⚡', '#f9ca24', '#f0932b', NULL)
ON CONFLICT (name) DO NOTHING;

-- Users table with settings
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,

    -- Selected personality
    active_personality_id INTEGER DEFAULT 1,

    -- Proactive settings
    proactive_enabled BOOLEAN DEFAULT true,
    messages_per_day INTEGER DEFAULT 10,
    active_hours_start TEXT DEFAULT '07:00',
    active_hours_end TEXT DEFAULT '23:00',
    timezone TEXT DEFAULT 'UTC',

    -- Boost mode
    boost_mode BOOLEAN DEFAULT false,
    boost_expires_at TIMESTAMP,

    -- Pause
    paused_until TIMESTAMP,

    -- Stats
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (active_personality_id) REFERENCES personalities(id)
);

-- User context - goals, struggles, wins
CREATE TABLE IF NOT EXISTS user_context (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    context_type TEXT NOT NULL, -- 'goal', 'struggle', 'win', 'important_date'
    content TEXT NOT NULL,
    priority TEXT DEFAULT 'medium', -- 'low', 'medium', 'high'
    mentioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_context_user ON user_context(user_id);
CREATE INDEX IF NOT EXISTS idx_context_type ON user_context(context_type);

-- Goals with progress tracking
CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'active', -- 'active', 'completed', 'paused'
    progress INTEGER DEFAULT 0, -- 0-100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);

-- Message history
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    message_type TEXT, -- 'reactive', 'proactive_checkin', 'proactive_reminder', etc.
    tokens_used INTEGER DEFAULT 0,
    rag_used BOOLEAN DEFAULT false,
    user_replied BOOLEAN DEFAULT false,
    reply_time_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type);

-- Scheduled proactive messages queue
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    message_type TEXT NOT NULL, -- 'morning', 'checkin', 'reminder', 'motivation', etc.
    priority INTEGER DEFAULT 5, -- 1-10, 1 = highest
    context_data TEXT, -- JSON with relevant context
    status TEXT DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'cancelled'
    sent_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scheduled_user ON scheduled_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_time ON scheduled_messages(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_status ON scheduled_messages(status);

-- Important dates and events
CREATE TABLE IF NOT EXISTS important_dates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    event_date DATE NOT NULL,
    description TEXT,
    reminder_frequency TEXT DEFAULT 'daily', -- 'daily', 'frequent', 'weekly'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dates_user ON important_dates(user_id);
CREATE INDEX IF NOT EXISTS idx_dates_date ON important_dates(event_date);

-- User activity log for analytics
CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL, -- 'message_sent', 'message_received', 'goal_created', etc.
    details TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC);
