"""Simple Telegram bot with RAG-powered James Clear personality."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from src.rag.embedder import EmbeddingGenerator
from src.rag.search import RAGSearchEngine
from src.ai.deepseek_client import DeepSeekClient, JAMES_CLEAR_PROMPT

# Load environment variables
load_dotenv()


class JamesClearBot:
    """Telegram bot with James Clear personality."""

    def __init__(self):
        """Initialize bot components."""
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

        # Initialize RAG components
        print("🔧 Initializing RAG system...")
        self.embedder = EmbeddingGenerator()
        self.search_engine = RAGSearchEngine(
            persist_directory="./data/chroma_db",
            collection_name="james_clear_atomic_habits"
        )

        # Initialize AI client
        self.ai_client = DeepSeekClient()

        # Store conversation history per user
        self.conversations = {}

        print("✅ Bot initialized and ready!")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        welcome_message = f"""
Привет, {user.first_name}! 👋

Я Джеймс Клир - автор книги "Атомные привычки".

Я помогу тебе:
• Сформировать полезные привычки
• Избавиться от вредных
• Достичь целей через маленькие изменения

Просто напиши мне свой вопрос или проблему, и я дам конкретные советы на основе моей книги.

📚 У меня есть доступ ко всему содержанию "Атомных привычек" через RAG систему.

Команды:
/start - это сообщение
/clear - очистить историю диалога
/help - помощь
        """

        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🤖 Как со мной работать:

1. Задавай конкретные вопросы про привычки
2. Описывай свои проблемы с мотивацией
3. Спрашивай про системы и фреймворки
4. Делись своими целями

Я буду отвечать на основе моей книги "Атомные привычки", используя релевантные отрывки.

Примеры вопросов:
• Как начать бегать по утрам?
• Почему я откладываю важные дела?
• Как сформировать привычку читать?
• Что такое habit stacking?
        """

        await update.message.reply_text(help_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear conversation history."""
        user_id = update.effective_user.id

        if user_id in self.conversations:
            del self.conversations[user_id]

        await update.message.reply_text("✅ История диалога очищена. Начнем заново!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user messages."""
        user_id = update.effective_user.id
        user_message = update.message.text

        # Show typing indicator
        await update.message.chat.send_action(action="typing")

        # Get or create conversation history
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        # Generate response with RAG
        try:
            response = self.ai_client.generate_with_rag(
                user_message=user_message,
                search_engine=self.search_engine,
                embedder=self.embedder,
                system_prompt=JAMES_CLEAR_PROMPT,
                conversation_history=self.conversations[user_id],
                n_results=3,
                temperature=0.7
            )

            # Update conversation history
            self.conversations[user_id].append({
                "role": "user",
                "content": user_message
            })
            self.conversations[user_id].append({
                "role": "assistant",
                "content": response['answer']
            })

            # Keep only last 10 messages
            if len(self.conversations[user_id]) > 20:
                self.conversations[user_id] = self.conversations[user_id][-20:]

            # Send response
            reply = response['answer']

            # Add footer with stats (optional)
            if response.get('rag_used'):
                reply += f"\n\n💡 _Использовано {response['rag_chunks']} отрывков из книги_"

            await update.message.reply_text(reply, parse_mode='Markdown')

        except Exception as e:
            error_msg = f"❌ Произошла ошибка: {str(e)}"
            await update.message.reply_text(error_msg)
            print(f"Error handling message: {e}")

    def run(self):
        """Start the bot."""
        print(f"\n🚀 Starting Telegram bot...")

        # Create application
        app = Application.builder().token(self.token).build()

        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("clear", self.clear_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Start bot
        print("✅ Bot is running! Press Ctrl+C to stop.\n")
        app.run_polling()


if __name__ == "__main__":
    # Check if RAG system is set up
    db_path = "./data/chroma_db"
    if not os.path.exists(db_path) or not os.listdir(db_path):
        print("⚠️  WARNING: ChromaDB not found or empty!")
        print(f"   Expected location: {db_path}")
        print("\n📚 Please run the ingestion script first:")
        print("   python scripts/ingest_book.py")
        print("\nContinuing anyway...\n")

    # Create and run bot
    bot = JamesClearBot()
    bot.run()
