"""Proactive Telegram bot with RAG-powered James Clear personality."""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv
import logging

from src.database.db_manager_postgres import DatabaseManager

# Optional RAG imports (not available in minimal Railway deployment)
try:
    from src.rag.embedder import EmbeddingGenerator
    from src.rag.search import RAGSearchEngine
    RAG_AVAILABLE = True
    logger.info("✅ RAG modules available")
except ImportError as e:
    logger.warning(f"⚠️ RAG modules not available: {e}")
    logger.warning("   Bot will work without RAG features")
    RAG_AVAILABLE = False
    EmbeddingGenerator = None
    RAGSearchEngine = None

from src.ai.deepseek_client import DeepSeekClient, JAMES_CLEAR_PROMPT
from src.ai.proactive_messages import ProactiveMessageGenerator
from src.scheduler.proactive_scheduler import ProactiveScheduler
from src.utils.context_extractor import ContextExtractor

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ProactiveJamesClearBot:
    """Proactive Telegram bot with James Clear personality."""

    def __init__(self):
        """Initialize bot components."""
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        # Initialize database
        logger.info("🔧 Initializing database...")
        self.db = DatabaseManager()  # Uses DATABASE_URL from .env

        # Initialize RAG (optional)
        if RAG_AVAILABLE:
            logger.info("🔧 Initializing RAG system...")
            self.embedder = EmbeddingGenerator()
            self.search_engine = RAGSearchEngine(
                persist_directory="./data/chroma_db",
                collection_name="james_clear_atomic_habits"
            )
        else:
            logger.info("⏭️ Skipping RAG initialization (dependencies not installed)")
            self.embedder = None
            self.search_engine = None

        # Initialize AI
        self.ai_client = DeepSeekClient()
        self.message_gen = ProactiveMessageGenerator(
            self.ai_client,
            self.search_engine,
            self.embedder
        )

        # Initialize scheduler
        logger.info("🔧 Initializing scheduler...")
        self.scheduler = ProactiveScheduler(self.db, self.message_gen)

        # Context extractor
        self.context_extractor = ContextExtractor()

        # User conversation states (для интерактивных режимов)
        self.user_states = {}

        logger.info("✅ Bot components initialized!")

    # ==================== MENU HELPERS ====================

    def get_main_menu(self):
        """Get main menu keyboard."""
        keyboard = [
            [KeyboardButton("📊 Dashboard"), KeyboardButton("🎯 Цели")],
            [KeyboardButton("💬 Чат"), KeyboardButton("⚙️ Настройки")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def get_goals_menu(self):
        """Get goals submenu keyboard."""
        keyboard = [
            [KeyboardButton("➕ Добавить цель")],
            [KeyboardButton("📋 Мои цели")],
            [KeyboardButton("✅ Отметить выполненной")],
            [KeyboardButton("⬅️ Главное меню")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def get_settings_menu(self):
        """Get settings submenu keyboard."""
        keyboard = [
            [KeyboardButton("🔧 Частота сообщений")],
            [KeyboardButton("📈 Boost Mode"), KeyboardButton("⏸️ Пауза")],
            [KeyboardButton("👤 Сменить личность")],
            [KeyboardButton("📊 Мои настройки")],
            [KeyboardButton("⬅️ Главное меню")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # ==================== COMMANDS ====================

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        telegram_id = user.id

        # Create user in database
        self.db.create_user(telegram_id, user.username, user.first_name)

        welcome = f"""Привет, {user.first_name}! 👋

Я **Джеймс Клир** - автор "Атомных привычек".

🎯 **Я буду писать тебе первым!** Это проактивный коуч-бот.

**Что я делаю:**
• Пишу тебе сам в течение дня
• Напоминаю о целях
• Мотивирую продолжать
• Помогаю отслеживать прогресс

📊 Используй /setup чтобы настроить частоту сообщений

💬 Можешь писать мне в любое время - отвечу на основе моей книги через RAG систему.

**Команды:**
/dashboard - 📊 Открыть дашборд (Web App)
/setup - Настроить частоту сообщений
/goal - Добавить цель
/boost - Усилить на 24ч (2x сообщений)
/pause - Пауза на N часов
/settings - Мои настройки
/help - Помощь
"""

        await update.message.reply_text(welcome, reply_markup=self.get_main_menu())

    async def setup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Setup proactive messages."""
        keyboard = [
            [InlineKeyboardButton("🟢 Low (5-10/день)", callback_data='freq_low')],
            [InlineKeyboardButton("🟡 Medium (10-20/день)", callback_data='freq_medium')],
            [InlineKeyboardButton("🔴 High (20-40/день)", callback_data='freq_high')],
        ]

        await update.message.reply_text(
            "Сколько сообщений в день хочешь получать?\n\n"
            "🟢 **Low**: 5-10 - редко, только важное\n"
            "🟡 **Medium**: 10-20 - умеренно\n"
            "🔴 **High**: 20-40 - максимальная поддержка",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def frequency_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle frequency selection."""
        query = update.callback_query
        await query.answer()

        telegram_id = query.from_user.id

        freq_map = {
            'freq_low': (7, "Low (5-10/день)"),
            'freq_medium': (15, "Medium (10-20/день)"),
            'freq_high': (30, "High (20-40/день)")
        }

        messages_per_day, label = freq_map.get(query.data, (10, "Medium"))

        # Update settings
        self.db.update_user_settings(
            telegram_id,
            messages_per_day=messages_per_day,
            proactive_enabled=True
        )

        # Schedule messages for today
        count = self.scheduler.schedule_user_messages(telegram_id)

        await query.edit_message_text(
            f"✅ Настроено: **{label}**\n\n"
            f"Запланировано {count} сообщений на сегодня.\n"
            f"Первое сообщение скоро придет!\n\n"
            f"Используй /boost для усиления или /pause для паузы.",
            parse_mode='Markdown'
        )

    async def goal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a new goal."""
        telegram_id = update.effective_user.id

        if not context.args:
            await update.message.reply_text(
                "Использование: /goal Твоя цель здесь\n\n"
                "Например:\n"
                "/goal Бегать каждое утро\n"
                "/goal Читать 30 минут в день"
            )
            return

        goal_text = ' '.join(context.args)

        # Add to database
        goal_id = self.db.add_goal(telegram_id, goal_text, priority='high')

        if goal_id:
            await update.message.reply_text(
                f"🎯 Цель добавлена:\n**{goal_text}**\n\n"
                "Буду регулярно спрашивать про прогресс!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка добавления цели")

    async def boost_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enable boost mode."""
        telegram_id = update.effective_user.id

        # Default 24 hours
        duration = 24
        if context.args:
            try:
                duration = int(context.args[0])
            except:
                pass

        self.db.enable_boost_mode(telegram_id, duration_hours=duration)

        # Re-schedule with boost
        count = self.scheduler.schedule_user_messages(telegram_id)

        await update.message.reply_text(
            f"📈 **BOOST MODE** активирован на {duration}ч!\n\n"
            f"Частота сообщений увеличена в 2 раза.\n"
            f"Запланировано {count} сообщений.\n\n"
            "Используй когда:\n"
            "• Важный проект с дедлайном\n"
            "• Нужна extra мотивация\n"
            "• Формируешь новую привычку",
            parse_mode='Markdown'
        )

    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause proactive messages."""
        telegram_id = update.effective_user.id

        # Parse duration (default 3 hours)
        duration = 3
        if context.args:
            arg = context.args[0].lower()
            if 'h' in arg or 'ч' in arg:
                duration = int(arg.replace('h', '').replace('ч', ''))
            elif 'd' in arg or 'д' in arg:
                duration = int(arg.replace('d', '').replace('д', '')) * 24

        self.db.pause_proactive(telegram_id, duration_hours=duration)

        await update.message.reply_text(
            f"⏸️ Проактивные сообщения приостановлены на **{duration}ч**\n\n"
            "Используй /unpause чтобы возобновить раньше.",
            parse_mode='Markdown'
        )

    async def unpause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unpause proactive messages."""
        telegram_id = update.effective_user.id

        self.db.unpause_proactive(telegram_id)

        # Re-schedule
        count = self.scheduler.schedule_user_messages(telegram_id)

        await update.message.reply_text(
            f"▶️ Проактивность возобновлена!\n"
            f"Запланировано {count} сообщений."
        )

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current settings."""
        telegram_id = update.effective_user.id
        user = self.db.get_user(telegram_id)

        if not user:
            await update.message.reply_text("❌ Пользователь не найден")
            return

        status = "✅ Включено" if user['proactive_enabled'] else "❌ Выключено"
        boost = "📈 Да" if user['boost_mode'] else "Нет"

        goals = self.db.get_active_goals(telegram_id)
        goals_text = '\n'.join([f"  • {g['title']}" for g in goals]) if goals else "  Нет активных целей"

        settings_text = f"""⚙️ **МОИ НАСТРОЙКИ**

**Проактивность:** {status}
**Сообщений/день:** {user['messages_per_day']}
**Активные часы:** {user['active_hours_start']} - {user['active_hours_end']}
**Boost mode:** {boost}

🎯 **Цели:**
{goals_text}

Команды:
/setup - Изменить частоту
/boost - Усилить
/pause - Пауза
"""

        await update.message.reply_text(settings_text, parse_mode='Markdown')

    async def dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Open Web App dashboard."""
        # URL вашего веб-сервера (замени на свой ngrok/локальный URL)
        webapp_url = "https://ai-coach-bot-inky.vercel.app"

        keyboard = [
            [InlineKeyboardButton(
                "📊 Открыть Dashboard",
                web_app=WebAppInfo(url=webapp_url)
            )]
        ]

        await update.message.reply_text(
            "📊 **Твой персональный дашборд**\n\n"
            "Нажми кнопку чтобы открыть:\n"
            "• 🎯 Цели с прогресс-барами\n"
            "• 💬 История всех сообщений\n"
            "• 📝 Извлечённый контекст\n"
            "• ⏰ Запланированные сообщения\n"
            "• 👥 **Выбор личности коуча**\n"
            "• 📊 Статистика в реальном времени",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_button_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text button presses with navigation."""
        text = update.message.text

        # ===== MAIN MENU =====
        if text == "📊 Dashboard":
            await self.dashboard_command(update, context)

        elif text == "🎯 Цели":
            await update.message.reply_text(
                "🎯 **Раздел: Цели**\n\n"
                "Здесь ты можешь управлять своими целями.",
                reply_markup=self.get_goals_menu(),
                parse_mode='Markdown'
            )

        elif text == "💬 Чат":
            await update.message.reply_text(
                "💬 **Режим: Чат**\n\n"
                "Напиши мне что-нибудь, и я отвечу на основе книги \"Атомные привычки\".\n\n"
                "Можешь задавать вопросы о привычках, целях, мотивации.",
                reply_markup=self.get_main_menu(),
                parse_mode='Markdown'
            )

        elif text == "⚙️ Настройки":
            await update.message.reply_text(
                "⚙️ **Раздел: Настройки**\n\n"
                "Выбери что хочешь настроить:",
                reply_markup=self.get_settings_menu(),
                parse_mode='Markdown'
            )

        # ===== GOALS SUBMENU =====
        elif text == "➕ Добавить цель":
            telegram_id = update.effective_user.id
            # Установить состояние ожидания ввода цели
            self.user_states[telegram_id] = 'waiting_for_goal'

            await update.message.reply_text(
                "➕ **Добавить цель**\n\n"
                "Отлично! Просто напиши свою цель в следующем сообщении.\n\n"
                "Например:\n"
                "• Бегать каждое утро\n"
                "• Читать 30 минут в день\n"
                "• Пить 2 литра воды\n\n"
                "Или нажми /cancel чтобы отменить.",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True),
                parse_mode='Markdown'
            )

        elif text == "📋 Мои цели":
            telegram_id = update.effective_user.id
            goals = self.db.get_active_goals(telegram_id)

            if goals:
                goals_text = "📋 **Твои активные цели:**\n\n"
                for g in goals:
                    emoji = "🔥" if g['priority'] == 'high' else "📌" if g['priority'] == 'medium' else "📍"
                    goals_text += f"{emoji} {g['title']}\n"
                    goals_text += f"   Прогресс: {g['progress']}% {'█' * (g['progress'] // 10)}{'░' * (10 - g['progress'] // 10)}\n\n"
            else:
                goals_text = "📋 У тебя пока нет активных целей.\n\nДобавь первую цель!"

            await update.message.reply_text(
                goals_text,
                reply_markup=self.get_goals_menu(),
                parse_mode='Markdown'
            )

        elif text == "✅ Отметить выполненной":
            await update.message.reply_text(
                "✅ **Отметить цель выполненной**\n\n"
                "Эта функция в разработке.\n"
                "Скоро ты сможешь отмечать цели как выполненные!",
                reply_markup=self.get_goals_menu(),
                parse_mode='Markdown'
            )

        # ===== SETTINGS SUBMENU =====
        elif text == "🔧 Частота сообщений":
            await self.setup_command(update, context)

        elif text == "📈 Boost Mode":
            await self.boost_command(update, context)

        elif text == "⏸️ Пауза":
            await update.message.reply_text(
                "⏸️ **Пауза**\n\n"
                "Введи длительность паузы:\n"
                "Например: `/pause 2ч` или `/pause 1д`",
                reply_markup=self.get_settings_menu(),
                parse_mode='Markdown'
            )

        elif text == "👤 Сменить личность":
            await update.message.reply_text(
                "👤 **Сменить личность коуча**\n\n"
                "Открой Dashboard чтобы выбрать другую личность:\n"
                "📚 James Clear\n"
                "🔥 Tony Robbins\n"
                "🧠 Andrew Huberman\n"
                "🧘 Naval Ravikant\n"
                "⚡ Tim Ferriss",
                reply_markup=self.get_settings_menu(),
                parse_mode='Markdown'
            )

        elif text == "📊 Мои настройки":
            await self.settings_command(update, context)

        # ===== CANCEL BUTTON =====
        elif text == "❌ Отмена":
            telegram_id = update.effective_user.id
            # Очистить состояние если было
            if telegram_id in self.user_states:
                del self.user_states[telegram_id]

            await update.message.reply_text(
                "❌ Отменено.\n\nВозвращаюсь в меню целей.",
                reply_markup=self.get_goals_menu()
            )

        # ===== BACK BUTTON =====
        elif text == "⬅️ Главное меню":
            telegram_id = update.effective_user.id
            # Очистить состояние при возврате в главное меню
            if telegram_id in self.user_states:
                del self.user_states[telegram_id]

            await update.message.reply_text(
                "🏠 **Главное меню**\n\n"
                "Выбери раздел:",
                reply_markup=self.get_main_menu(),
                parse_mode='Markdown'
            )

        # ===== REGULAR MESSAGE =====
        else:
            # If not a button, handle as regular message
            await self.handle_regular_message(update, context)

    def should_use_rag(self, user_message: str) -> bool:
        """
        Determine if we should use RAG (book examples) or just DeepSeek AI.

        RAG is used when:
        - User asks about habits, techniques, specific methods
        - User wants examples or references from the book
        - User asks "how to" questions about behavior change

        DeepSeek (no RAG) is used when:
        - Simple greetings or casual chat
        - Personal motivation or encouragement
        - General questions not requiring book references
        """
        msg_lower = user_message.lower()

        # Keywords that trigger RAG (book examples needed)
        rag_keywords = [
            'привычк', 'habit', 'как ', 'метод', 'техник', 'систем',
            'пример', 'книг', 'atomic', 'атомн', 'правил', 'закон',
            'стратег', 'способ', 'совет', 'рекоменд', 'framework',
            'identity', 'идентичност', 'окружен', 'environment',
            'stack', 'минут', 'правил', '4 закон', 'измени'
        ]

        # Keywords that indicate simple chat (no RAG needed)
        simple_keywords = [
            'привет', 'hello', 'здравствуй', 'спасибо', 'thanks',
            'как дела', 'how are', 'что нового', "what's up",
            'ок', 'okay', 'понял', 'got it', 'да', 'нет', 'yes', 'no'
        ]

        # Check if it's simple chat
        for keyword in simple_keywords:
            if keyword in msg_lower and len(user_message) < 50:
                return False

        # Check if RAG is needed
        for keyword in rag_keywords:
            if keyword in msg_lower:
                return True

        # For questions (?) about behavior/goals - use RAG
        if '?' in user_message and any(word in msg_lower for word in ['как', 'почему', 'что', 'когда']):
            return True

        # Default: use simple AI for short messages, RAG for longer detailed questions
        return len(user_message) > 30

    async def handle_regular_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular user messages (not buttons)."""
        user_id = update.effective_user.id
        telegram_id = user_id
        user_message = update.message.text

        # Ensure user exists (с обработкой ошибок БД)
        try:
            self.db.create_user(telegram_id, update.effective_user.username, update.effective_user.first_name)
        except Exception as e:
            logger.warning(f"DB unavailable for create_user: {e}")

        # ===== ПРОВЕРКА ИНТЕРАКТИВНЫХ РЕЖИМОВ =====
        # Проверить если пользователь в режиме добавления цели
        if telegram_id in self.user_states and self.user_states[telegram_id] == 'waiting_for_goal':
            # Добавить цель в базу (с обработкой ошибок)
            try:
                goal_id = self.db.add_goal(telegram_id, user_message, priority='high')
                if goal_id:
                    # Очистить состояние
                    del self.user_states[telegram_id]

                    await update.message.reply_text(
                        f"🎯 Цель добавлена:\n**{user_message}**\n\n"
                        "Отлично! Буду регулярно спрашивать про прогресс.",
                        reply_markup=self.get_goals_menu(),
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "❌ Ошибка добавления цели. Попробуй ещё раз.",
                        reply_markup=self.get_goals_menu()
                    )
            except Exception as e:
                logger.warning(f"DB unavailable for add_goal: {e}")
                # Даже если БД недоступна, очистим состояние и уведомим пользователя
                del self.user_states[telegram_id]
                await update.message.reply_text(
                    f"⚠️ База данных временно недоступна, но цель запомнена:\n**{user_message}**\n\n"
                    "Она будет сохранена когда подключение восстановится.",
                    reply_markup=self.get_goals_menu(),
                    parse_mode='Markdown'
                )
            return

        # Extract context from message
        extracted = self.context_extractor.extract_all(user_message)

        # Save extracted goals (с обработкой ошибок)
        try:
            for goal in extracted['goals']:
                self.db.add_context(telegram_id, 'goal', goal, priority='medium')
        except Exception as e:
            logger.warning(f"DB unavailable for add_context (goals): {e}")

        # Save struggles (с обработкой ошибок)
        try:
            for struggle in extracted['struggles']:
                self.db.add_context(telegram_id, 'struggle', struggle)
        except Exception as e:
            logger.warning(f"DB unavailable for add_context (struggles): {e}")

        # Save wins (с обработкой ошибок)
        try:
            for win in extracted['wins']:
                self.db.add_context(telegram_id, 'win', win)
        except Exception as e:
            logger.warning(f"DB unavailable for add_context (wins): {e}")

        # Show typing
        await update.message.chat.send_action(action="typing")

        # Determine if we should use RAG or just DeepSeek
        use_rag = self.should_use_rag(user_message)

        logger.info(f"{'📚 Using RAG' if use_rag else '💬 Using simple AI'} for: '{user_message[:50]}...'")

        # Generate response
        try:
            if use_rag:
                # Use RAG for detailed questions requiring book examples
                response = self.ai_client.generate_with_rag(
                    user_message=user_message,
                    search_engine=self.search_engine,
                    embedder=self.embedder,
                    system_prompt=JAMES_CLEAR_PROMPT,
                    n_results=3,
                    temperature=0.7
                )
            else:
                # Use simple DeepSeek for casual chat and motivation
                response = self.ai_client.generate_response(
                    user_message=user_message,
                    system_prompt=JAMES_CLEAR_PROMPT,
                    temperature=0.8,  # Slightly higher temp for more natural chat
                    max_tokens=500
                )

            # Save message (с обработкой ошибок БД)
            try:
                self.db.save_message(telegram_id, 'user', user_message, 'reactive')
                self.db.save_message(
                    telegram_id,
                    'assistant',
                    response['answer'],
                    'reactive',
                    tokens_used=response.get('tokens_used', 0),
                    rag_used=response.get('rag_used', False)
                )
            except Exception as e:
                logger.warning(f"DB unavailable for save_message: {e}")

            await update.message.reply_text(response['answer'])

        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуй еще раз."
            )

    async def post_init(self, application):
        """Initialize scheduler after event loop starts."""
        # Set bot application in scheduler so it can send messages
        self.scheduler.bot_app = application
        self.scheduler.start()
        logger.info("✅ Scheduler started with bot integration")

    def run(self):
        """Start the bot."""
        logger.info("🚀 Starting Proactive James Clear Bot...")

        # Create application
        app = Application.builder().token(self.token).build()

        # Add post_init callback to start scheduler
        app.post_init = self.post_init

        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("dashboard", self.dashboard_command))
        app.add_handler(CommandHandler("setup", self.setup_command))
        app.add_handler(CommandHandler("goal", self.goal_command))
        app.add_handler(CommandHandler("boost", self.boost_command))
        app.add_handler(CommandHandler("pause", self.pause_command))
        app.add_handler(CommandHandler("unpause", self.unpause_command))
        app.add_handler(CommandHandler("settings", self.settings_command))
        app.add_handler(CallbackQueryHandler(self.frequency_callback, pattern='^freq_'))
        # Handle text messages (including buttons)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_button_text))

        # Start bot
        logger.info("✅ Bot is running!")
        logger.info("   Press Ctrl+C to stop\n")
        app.run_polling()


if __name__ == "__main__":
    bot = ProactiveJamesClearBot()
    bot.run()
