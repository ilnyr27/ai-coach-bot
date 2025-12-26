"""DeepSeek AI client with RAG integration."""

from openai import OpenAI
import os
from typing import List, Dict, Optional


class DeepSeekClient:
    """Client for DeepSeek API with RAG support."""

    def __init__(self, api_key: str = None, base_url: str = "https://api.deepseek.com"):
        """
        Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key (or use DEEPSEEK_API_KEY env var)
            base_url: API base URL
        """
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')

        if not self.api_key:
            raise ValueError("DeepSeek API key not provided. Set DEEPSEEK_API_KEY env var or pass api_key parameter.")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

        print(f"✅ DeepSeek client initialized")

    def generate_response(
        self,
        user_message: str,
        system_prompt: str = None,
        conversation_history: List[Dict] = None,
        rag_context: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict:
        """
        Generate AI response with optional RAG context.

        Args:
            user_message: User's message
            system_prompt: System prompt (personality definition)
            conversation_history: Previous messages
            rag_context: Retrieved context from RAG
            temperature: Sampling temperature
            max_tokens: Max response tokens

        Returns:
            Dict with response and metadata
        """
        # Build system prompt with RAG context
        final_system_prompt = system_prompt or "Ты мудрый наставник."

        if rag_context:
            rag_text = self._format_rag_context(rag_context)
            final_system_prompt += f"\n\n📚 КОНТЕКСТ ИЗ КНИГИ:\n{rag_text}"

        # Build messages
        messages = [
            {"role": "system", "content": final_system_prompt}
        ]

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Make API call
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            return {
                'answer': answer,
                'tokens_used': tokens_used,
                'rag_used': bool(rag_context),
                'rag_chunks': len(rag_context) if rag_context else 0
            }

        except Exception as e:
            print(f"❌ DeepSeek API error: {e}")
            return {
                'answer': f"Извини, произошла ошибка: {str(e)}",
                'tokens_used': 0,
                'rag_used': False,
                'error': str(e)
            }

    def generate_with_rag(
        self,
        user_message: str,
        search_engine,
        embedder,
        system_prompt: str = None,
        conversation_history: List[Dict] = None,
        n_results: int = 3,
        temperature: float = 0.7
    ) -> Dict:
        """
        Generate response with automatic RAG retrieval.

        Args:
            user_message: User's message
            search_engine: RAGSearchEngine instance
            embedder: EmbeddingGenerator instance
            system_prompt: Personality prompt
            conversation_history: Previous messages
            n_results: Number of RAG chunks to retrieve
            temperature: Sampling temperature

        Returns:
            Dict with response and metadata
        """
        # Retrieve relevant context from RAG
        print(f"🔍 Searching RAG for: '{user_message[:50]}...'")

        rag_results = search_engine.search_with_embedder(
            query=user_message,
            embedder=embedder,
            n_results=n_results
        )

        print(f"✅ Found {len(rag_results)} relevant chunks")

        # Generate response with context
        return self.generate_response(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            rag_context=rag_results,
            temperature=temperature
        )

    def _format_rag_context(self, rag_results: List[Dict]) -> str:
        """
        Format RAG results for prompt.

        Args:
            rag_results: List of retrieved chunks

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, result in enumerate(rag_results, 1):
            chapter = result['metadata'].get('chapter_title', 'Unknown')
            text = result['text']

            context_parts.append(f"[Отрывок {i} из главы '{chapter}']:\n{text}")

        return "\n\n".join(context_parts)


# Personality prompts
JAMES_CLEAR_PROMPT = """
Ты Джеймс Клир - автор бестселлера "Атомные привычки" (Atomic Habits).

Твоя философия:
- Маленькие изменения → огромные результаты (1% улучшений каждый день)
- Системы важнее целей
- Изменение идентичности, а не просто поведения
- 4 закона изменения поведения: сделать очевидным, привлекательным, легким, приносящим удовлетворение

Твой стиль:
- Конкретные, практичные советы без воды
- Реальные примеры и истории
- Простые фреймворки и системы
- Фокус на действии, а не теории

Ключевые концепции:
- Habit stacking (наслоение привычек)
- 2-minute rule (правило 2 минут)
- Environment design (дизайн окружения)
- Identity-based habits (привычки основанные на идентичности)

Отвечай кратко (2-4 абзаца), давай конкретные шаги, используй примеры.
"""


if __name__ == "__main__":
    # Test client
    from dotenv import load_dotenv
    load_dotenv()

    print("🧪 Testing DeepSeek Client\n")

    # Initialize client
    client = DeepSeekClient()

    # Test simple generation
    test_message = "Как мне начать бегать по утрам? Я всегда откладываю."

    print(f"💬 User: {test_message}\n")

    response = client.generate_response(
        user_message=test_message,
        system_prompt=JAMES_CLEAR_PROMPT
    )

    print(f"🤖 James Clear:\n{response['answer']}\n")
    print(f"📊 Stats:")
    print(f"   Tokens used: {response['tokens_used']}")
    print(f"   RAG used: {response['rag_used']}")
