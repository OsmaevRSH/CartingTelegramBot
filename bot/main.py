#!/usr/bin/env python3
"""
Точка входа Telegram-бота CartingBot
"""
import sys
import os

# bot/main.py → bot/ → project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.handlers.bot import main

if __name__ == "__main__":
    main()
