#!/bin/bash

# Start script for AI Coach Bot on Beget

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Run bot
python src/bot/proactive_bot.py
