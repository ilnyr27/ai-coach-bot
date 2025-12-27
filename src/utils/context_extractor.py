"""Simple context extraction from user messages."""

import re
from typing import List, Tuple, Optional


class ContextExtractor:
    """Extract goals, struggles, wins from user messages."""

    # Patterns for goal detection
    GOAL_PATTERNS = [
        r"хочу\s+(.+?)(?:[.!?]|$)",
        r"планирую\s+(.+?)(?:[.!?]|$)",
        r"нужно\s+(.+?)(?:[.!?]|$)",
        r"цель[\s:]+(.+?)(?:[.!?]|$)",
        r"мне\s+надо\s+(.+?)(?:[.!?]|$)",
        r"собираюсь\s+(.+?)(?:[.!?]|$)",
    ]

    # Patterns for struggles
    STRUGGLE_PATTERNS = [
        r"откладываю\s+(.+?)(?:[.!?]|$)",
        r"не\s+могу\s+(.+?)(?:[.!?]|$)",
        r"проблема\s+(.+?)(?:[.!?]|$)",
        r"сложно\s+(.+?)(?:[.!?]|$)",
        r"никак\s+не\s+(.+?)(?:[.!?]|$)",
    ]

    # Patterns for wins
    WIN_PATTERNS = [
        r"сделал\s+(.+?)(?:[.!?]|$)",
        r"получилось\s+(.+?)(?:[.!?]|$)",
        r"удалось\s+(.+?)(?:[.!?]|$)",
        r"добился\s+(.+?)(?:[.!?]|$)",
        r"выполнил\s+(.+?)(?:[.!?]|$)",
    ]

    @staticmethod
    def extract_goals(text: str) -> List[str]:
        """Extract potential goals from text."""
        goals = []

        for pattern in ContextExtractor.GOAL_PATTERNS:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            for match in matches:
                # Clean up
                goal = match.strip()
                if len(goal) > 10 and len(goal) < 200:  # Reasonable length
                    goals.append(goal)

        return goals

    @staticmethod
    def extract_struggles(text: str) -> List[str]:
        """Extract mentioned struggles/problems."""
        struggles = []

        for pattern in ContextExtractor.STRUGGLE_PATTERNS:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            for match in matches:
                struggle = match.strip()
                if len(struggle) > 5 and len(struggle) < 200:
                    struggles.append(struggle)

        return struggles

    @staticmethod
    def extract_wins(text: str) -> List[str]:
        """Extract mentioned achievements/wins."""
        wins = []

        for pattern in ContextExtractor.WIN_PATTERNS:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            for match in matches:
                win = match.strip()
                if len(win) > 5 and len(win) < 200:
                    wins.append(win)

        return wins

    @staticmethod
    def extract_all(text: str) -> dict:
        """Extract all context from text."""
        return {
            'goals': ContextExtractor.extract_goals(text),
            'struggles': ContextExtractor.extract_struggles(text),
            'wins': ContextExtractor.extract_wins(text)
        }

    @staticmethod
    def is_likely_goal(text: str) -> bool:
        """Check if text likely contains a goal."""
        text_lower = text.lower()

        goal_keywords = ['хочу', 'планирую', 'нужно', 'цель', 'собираюсь', 'мечтаю']

        return any(keyword in text_lower for keyword in goal_keywords)

    @staticmethod
    def is_likely_struggle(text: str) -> bool:
        """Check if text likely contains a struggle."""
        text_lower = text.lower()

        struggle_keywords = ['откладываю', 'не могу', 'проблема', 'сложно', 'никак']

        return any(keyword in text_lower for keyword in struggle_keywords)

    @staticmethod
    def extract_progress_percentage(text: str) -> Optional[int]:
        """
        Extract absolute progress percentage from numerical data in text.

        Returns:
            Progress percentage (0-100) or None

        Examples:
            "просмотрел 17 из 30 видео" -> 56
            "осталось 13 из 30" -> 56
            "прошел 3 блок из 3, осталось 13 из 30" -> 85 (complex case)
        """
        text_lower = text.lower()

        # PRIORITY 1: Multi-stage progress "блок X из Y, осталось/сделал A из B"
        # Match both "блок 1 из 3" and "прохожу 3 блок из 3"
        block_pattern = r'(?:блок|модуль|этап|глава|раздел)\s*(\d+)\s*из\s*(\d+)|(?:\w+\s+)?(\d+)\s+(?:блок|модуль|этап|глава|раздел)\s*из\s*(\d+)'
        block_match = re.search(block_pattern, text_lower)

        if block_match:
            # Handle two pattern alternatives (group 1-2 or group 3-4)
            current_block = int(block_match.group(1) or block_match.group(3))
            total_blocks = int(block_match.group(2) or block_match.group(4))

            # Check for sub-progress: "осталось X из Y" OR "сделал/прошел X из Y"
            remaining_match = re.search(r'осталось?\s*(\d+)(?:\s+\w+)?\s+из\s+(\d+)', text_lower)
            completed_match = re.search(r'(?:сделал|прошел|выполнил|просмотрел)\s*(\d+)\s*из\s*(\d+)', text_lower)

            if remaining_match:
                remaining = int(remaining_match.group(1))
                total_in_block = int(remaining_match.group(2))
                completed_in_block = total_in_block - remaining
                current_block_progress = completed_in_block / total_in_block if total_in_block > 0 else 0
            elif completed_match:
                completed_in_block = int(completed_match.group(1))
                total_in_block = int(completed_match.group(2))
                current_block_progress = completed_in_block / total_in_block if total_in_block > 0 else 0
            else:
                # Just block number, assume it's the completion percentage
                return min(100, int((current_block / total_blocks) * 100))

            # Calculate: (completed blocks + progress in current block) / total blocks
            completed_blocks = current_block - 1
            overall_progress = (completed_blocks + current_block_progress) / total_blocks
            return min(100, int(overall_progress * 100))

        # PRIORITY 2: Simple "осталось X из Y"
        remaining_pattern = r'осталось?\s*(\d+)(?:\s+\w+)?\s+из\s+(\d+)'
        remaining_match = re.search(remaining_pattern, text_lower)
        if remaining_match:
            remaining = int(remaining_match.group(1))
            total = int(remaining_match.group(2))
            if total > 0:
                completed = total - remaining
                return min(100, int((completed / total) * 100))

        # PRIORITY 3: Simple "X из Y" (completed X out of Y)
        completed_pattern = r'(?:просмотрел|прошел|сделал|прочитал|выполнил)?\s*(\d+)\s*из\s*(\d+)'
        completed_match = re.search(completed_pattern, text_lower)
        if completed_match:
            completed = int(completed_match.group(1))
            total = int(completed_match.group(2))
            if total > 0:
                return min(100, int((completed / total) * 100))

        return None

    @staticmethod
    def extract_progress_update(text: str) -> Optional[Tuple[str, int]]:
        """
        Extract goal progress update from text (legacy method - uses fixed increments).

        Returns:
            Tuple of (goal_keyword, progress_percentage) or None

        Examples:
            "Сегодня пробежал 5 км" -> increase progress
            "Выполнил задачу" -> increase progress
        """
        text_lower = text.lower()

        # Progress indicators (positive)
        positive_patterns = [
            (r'(пробежал|бегал|сделал|выполнил|прочитал|закончил)', 15),  # +15%
            (r'(продолжаю|делаю|занимаюсь)', 10),  # +10%
            (r'(попробовал|начал|приступил)', 5),  # +5%
        ]

        for pattern, increase in positive_patterns:
            if re.search(pattern, text_lower):
                # Try to extract what they did
                for goal_pattern in ContextExtractor.WIN_PATTERNS:
                    match = re.search(goal_pattern, text_lower)
                    if match:
                        activity = match.group(1).strip()
                        return (activity, increase)

                # Default return
                return ("прогресс", increase)

        return None


if __name__ == "__main__":
    # Test context extractor
    print("🧪 Testing ContextExtractor\n")

    test_messages = [
        "Хочу начать бегать по утрам, но постоянно откладываю.",
        "Планирую читать каждый день по 30 минут",
        "Сегодня сделал пробежку 5 км! Получилось!",
        "Не могу сосредоточиться на работе, прокрастинация",
        "Мне нужно закончить проект до 20 декабря"
    ]

    for msg in test_messages:
        print(f"📝 Message: {msg}")

        context = ContextExtractor.extract_all(msg)

        if context['goals']:
            print(f"   🎯 Goals: {context['goals']}")
        if context['struggles']:
            print(f"   ⚠️  Struggles: {context['struggles']}")
        if context['wins']:
            print(f"   ✅ Wins: {context['wins']}")

        print()

    print("✅ Context extractor test completed!")
