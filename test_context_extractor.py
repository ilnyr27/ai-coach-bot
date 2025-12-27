"""Test context extraction."""
# -*- coding: utf-8 -*-

import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.utils.context_extractor import ContextExtractor

# Test messages
test_messages = [
    "Хочу начать читать по арабски",
    "Моя цель - холодный душ каждый день",
    "Тяжело просыпаться рано утром",
    "Сегодня встал в 6 утра!",
    "Сейчас читаю арабский. Прохожу 3 блок из 3. Осталось 13 видео из 30."
]

print("Testing ContextExtractor.extract_all():\n")

for msg in test_messages:
    print(f"Message: {msg}")
    result = ContextExtractor.extract_all(msg)
    print(f"  Goals: {result['goals']}")
    print(f"  Struggles: {result['struggles']}")
    print(f"  Wins: {result['wins']}")
    print(f"  Progress: {result['progress']}")
    print()
