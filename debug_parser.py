"""Debug the parser for your specific case."""
# -*- coding: utf-8 -*-

import sys
import io
import re

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

text = "Сейчас читаю арабский. Прохожу 3 блок из 3. Осталось 13 видео из 30."
text_lower = text.lower()

print(f"Input: {text}\n")

# Check block pattern
block_pattern = r'(?:блок|модуль|этап|глава|раздел)\s*(\d+)\s*из\s*(\d+)'
block_match = re.search(block_pattern, text_lower)
if block_match:
    print(f"Block match: блок {block_match.group(1)} из {block_match.group(2)}")

# Check remaining pattern
remaining_pattern = r'осталось?\s*(\d+)(?:\s+\w+)?\s+из\s+(\d+)'
remaining_match = re.search(remaining_pattern, text_lower)
if remaining_match:
    print(f"Remaining match: осталось {remaining_match.group(1)} из {remaining_match.group(2)}")
    print(f"Groups: {remaining_match.groups()}")

# Manual calculation
if block_match and remaining_match:
    current_block = int(block_match.group(1))
    total_blocks = int(block_match.group(2))
    remaining = int(remaining_match.group(1))
    total_in_block = int(remaining_match.group(2))

    completed_blocks = current_block - 1
    completed_in_block = total_in_block - remaining
    current_block_progress = completed_in_block / total_in_block

    print(f"\nCalculation:")
    print(f"  Completed blocks: {completed_blocks}")
    print(f"  Current block: {current_block}/{total_blocks}")
    print(f"  Progress in current block: {completed_in_block}/{total_in_block} = {current_block_progress:.2%}")
    print(f"  Overall: ({completed_blocks} + {current_block_progress:.3f}) / {total_blocks} = {((completed_blocks + current_block_progress) / total_blocks):.2%}")

    overall = int(((completed_blocks + current_block_progress) / total_blocks) * 100)
    print(f"\nFinal result: {overall}%")
    print(f"Expected: 85%")
