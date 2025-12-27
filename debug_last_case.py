"""Debug last failing case."""
# -*- coding: utf-8 -*-

import sys
import io
import re

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

text = "блок 1 из 3, сделал 10 из 20"
text_lower = text.lower()

print(f"Input: {text}\n")

# Check block pattern
block_pattern = r'(?:\w+\s+)?(\d+)\s+(?:блок|модуль|этап|глава|раздел)\s*из\s*(\d+)'
block_match = re.search(block_pattern, text_lower)
if block_match:
    print(f"Block match: блок {block_match.group(1)} из {block_match.group(2)}")
else:
    print("No block match!")

# Try alternative pattern
alt_pattern = r'(?:блок|модуль|этап|глава|раздел)\s*(\d+)\s*из\s*(\d+)'
alt_match = re.search(alt_pattern, text_lower)
if alt_match:
    print(f"Alternative match: блок {alt_match.group(1)} из {alt_match.group(2)}")

# Check completed pattern
completed_pattern = r'(?:сделал|прошел|выполнил|просмотрел)\s*(\d+)\s*из\s*(\d+)'
completed_match = re.search(completed_pattern, text_lower)
if completed_match:
    print(f"Completed match: {completed_match.group(1)} из {completed_match.group(2)}")
