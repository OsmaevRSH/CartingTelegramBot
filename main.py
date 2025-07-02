#!/usr/bin/env python3
"""
Главный файл для запуска CartingBot
"""
import sys
import os

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot.bot import main

if __name__ == "__main__":
    main() 