"""Proactive message generation with different message types."""

from typing import Dict, List, Optional
import json


class ProactiveMessageGenerator:
    """Generate personalized proactive messages using AI."""

    # Prompts for different message types
    PROMPTS = {
        'morning': """Ты Джеймс Клир, автор "Атомных привычек". Напиши короткое утреннее сообщение (2-3 предложения).

Контекст пользователя:
{context}

Стиль:
- Мотивирующий, но не давящий
- Спроси что планирует сегодня
- Если есть цели - упомяни одну из них
- Можешь напомнить про "правило 2 минут" или "habit stacking"

Пиши от первого лица, как будто ты реально Джеймс Клир.""",

        'midday': """Ты Джеймс Клир. Напиши короткое дневное сообщение (1-2 предложения).

Контекст:
{context}

Вариации:
- Спроси как идут дела с утренними планами
- Напомни о важности маленьких действий
- Проверь прогресс по цели

Коротко и по делу.""",

        'evening': """Ты Джеймс Клир. Напиши вечернее сообщение для рефлексии (2-3 предложения).

Контекст:
{context}

Фокус:
- Подведение итогов дня
- Что получилось? Что можно улучшить?
- Не ломай цепочку - даже если сегодня не получилось, завтра продолжай
- Можешь спросить про планы на завтра

Поддерживающий тон.""",

        'checkin': """Ты Джеймс Клир. Напиши очень короткий check-in (1-2 предложения).

Контекст:
{context}

Просто спроси как дела. Можешь:
- "Как прогресс?"
- "Что сейчас делаешь?"
- "Как настроение?"

Очень коротко, дружелюбно.""",

        'reminder': """Ты Джеймс Клир. Напомни про цель: "{goal_title}"

Контекст:
{context}

Стиль:
- Короткое напоминание (1-2 предложения)
- Спроси про прогресс или что мешает
- Можешь дать быстрый совет по формированию привычки

Не читай лекций, просто дружеское напоминание.""",

        'motivation': """Ты Джеймс Клир. Напиши мотивирующее сообщение (2-3 предложения).

Контекст:
{context}

Идеи:
- Маленькие улучшения = огромные результаты
- 1% лучше каждый день
- Фокус на системе, а не на целях
- Изменение идентичности

Вдохновляющий, но практичный тон.""",

        'reflection': """Ты Джеймс Клир. Предложи короткую рефлексию (1-2 предложения).

Контекст:
{context}

Вопросы для размышления:
- Какая привычка помогла сегодня?
- Что бы сделал по-другому?
- Какое маленькое действие можешь повторить завтра?

Провоцируй на размышление, но не давай готовые ответы.""",

        'celebration': """Ты Джеймс Клир. Пользователь достиг прогресса! Поздравь (2 предложения).

Контекст:
{context}

Стиль:
- Искренняя радость за прогресс
- Подчеркни важность постоянства
- Мотивируй продолжать

Празднуй успех, но напомни что это марафон, не спринт."""
    }

    def __init__(self, ai_client, rag_engine=None, embedder=None):
        """
        Initialize message generator.

        Args:
            ai_client: DeepSeekClient instance
            rag_engine: RAGSearchEngine instance (optional)
            embedder: EmbeddingGenerator instance (optional)
        """
        self.ai = ai_client
        self.rag = rag_engine
        self.embedder = embedder

    async def generate(
        self,
        message_type: str,
        user_context: Dict,
        use_rag: bool = False
    ) -> str:
        """
        Generate proactive message.

        Args:
            message_type: Type of message ('morning', 'evening', etc.)
            user_context: Dict with user's goals, recent messages, etc.
            use_rag: Whether to use RAG for this message

        Returns:
            Generated message text
        """
        # Get prompt template
        prompt_template = self.PROMPTS.get(message_type, self.PROMPTS['checkin'])

        # Format context
        context_str = self._format_context(user_context)

        # Build prompt
        if '{goal_title}' in prompt_template:
            # Reminder type - needs goal
            goal_title = user_context.get('current_goal', 'твоя цель')
            prompt = prompt_template.format(goal_title=goal_title, context=context_str)
        else:
            prompt = prompt_template.format(context=context_str)

        # Generate message
        if use_rag and self.rag and self.embedder:
            # Use RAG for depth
            response = await self.ai.generate_with_rag(
                user_message=prompt,
                search_engine=self.rag,
                embedder=self.embedder,
                system_prompt=self._get_james_clear_prompt(),
                n_results=2,  # Fewer chunks for proactive messages
                temperature=0.8  # More creative
            )
        else:
            # Simple generation without RAG
            response = await self.ai.generate_response(
                user_message=prompt,
                system_prompt=self._get_james_clear_prompt(),
                temperature=0.8,
                max_tokens=200  # Shorter for proactive messages
            )

        return response['answer']

    def _format_context(self, user_context: Dict) -> str:
        """Format user context into readable string."""
        parts = []

        # Active goals
        if 'goals' in user_context and user_context['goals']:
            goals_str = '\n'.join([f"- {g}" for g in user_context['goals'][:3]])
            parts.append(f"Активные цели пользователя:\n{goals_str}")

        # Recent struggles
        if 'struggles' in user_context and user_context['struggles']:
            parts.append(f"Недавние проблемы: {', '.join(user_context['struggles'][:2])}")

        # Recent wins
        if 'wins' in user_context and user_context['wins']:
            parts.append(f"Недавние успехи: {', '.join(user_context['wins'][:2])}")

        # Important dates
        if 'important_dates' in user_context and user_context['important_dates']:
            parts.append(f"Важные даты: {user_context['important_dates'][0]}")

        # Last activity info
        if 'last_messages' in user_context and user_context['last_messages']:
            last_msg = user_context['last_messages'][0]
            parts.append(f"Последнее обсуждение: {last_msg[:100]}...")

        if not parts:
            return "Нет дополнительного контекста."

        return '\n\n'.join(parts)

    def _get_james_clear_prompt(self) -> str:
        """Get base James Clear personality prompt."""
        return """Ты Джеймс Клир - автор бестселлера "Атомные привычки".

Твоя философия:
- Маленькие изменения → огромные результаты
- Системы важнее целей
- Изменение идентичности, а не поведения
- 4 закона: сделать очевидным, привлекательным, легким, приносящим удовлетворение

Стиль:
- Короткие, практичные сообщения
- Конкретные советы без воды
- Дружелюбный, поддерживающий тон
- Вопросы провоцируют на размышление

Пиши КОРОТКО - это проактивное сообщение, не лекция."""

    def generate_simple_checkin(self, goals: List[str] = None) -> str:
        """Generate very simple check-in without AI (for cost optimization)."""
        templates = [
            "Как дела? 👋",
            "Как прогресс?",
            "Что сейчас делаешь?",
            "Как настроение? Продуктивный день?",
            "Привет! Как день проходит?",
        ]

        if goals:
            goal_templates = [
                f"Как дела с '{goals[0]}'?",
                f"Прогресс по '{goals[0]}'?",
                f"Помнишь про '{goals[0]}'? Как идет?",
            ]
            templates.extend(goal_templates)

        import random
        return random.choice(templates)


if __name__ == "__main__":
    # Test message generator
    print("🧪 Testing ProactiveMessageGenerator\n")

    # Mock context
    test_context = {
        'goals': ['Бегать каждое утро', 'Читать 30 минут в день'],
        'struggles': ['Прокрастинация', 'Откладывание дел'],
        'wins': ['Пробежал 3 дня подряд'],
        'important_dates': ['Дедлайн проекта - 20.12'],
        'last_messages': ['Обсуждали как начать бегать по утрам']
    }

    gen = ProactiveMessageGenerator(None)

    # Test simple messages
    print("💬 Simple check-ins:")
    for i in range(3):
        msg = gen.generate_simple_checkin(test_context['goals'])
        print(f"   {i+1}. {msg}")

    # Test context formatting
    print("\n📋 Formatted context:")
    context_str = gen._format_context(test_context)
    print(context_str)

    # Test prompt generation
    print("\n📝 Morning prompt example:")
    prompt = gen.PROMPTS['morning'].format(context=context_str)
    print(prompt[:200] + "...")

    print("\n✅ Message generator test completed!")
