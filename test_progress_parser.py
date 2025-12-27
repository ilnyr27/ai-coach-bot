"""Test the new progress percentage extraction."""
# -*- coding: utf-8 -*-

import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, 'src')

from utils.context_extractor import ContextExtractor

# Test cases
test_cases = [
    # Simple cases
    ("просмотрел 17 из 30 видео", 56),
    ("осталось 13 из 30", 56),
    ("прочитал 25 из 100 страниц", 25),

    # Complex multi-stage case (your example)
    ("Сейчас читаю арабский. Прохожу 3 блок из 3. Осталось 13 видео из 30.", 85),

    # Other multi-stage examples
    ("прохожу 2 модуль из 4, осталось 5 из 10 уроков", 37),  # (1 + 0.5) / 4 = 37.5%
    ("блок 1 из 3, сделал 10 из 20", 16),  # (0 + 0.5) / 3 = 16.6%
]

print("Testing progress percentage extraction:\n")

for text, expected in test_cases:
    result = ContextExtractor.extract_progress_percentage(text)
    status = "✓" if result == expected else "✗"
    print(f"{status} Input: {text}")
    print(f"   Expected: {expected}%, Got: {result}%")
    if result != expected:
        print(f"   DIFFERENCE: {abs(result - expected) if result else 'N/A'}%")
    print()
