# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директории для логов и базы данных
RUN mkdir -p logs data

# Создаем config/__init__.py если не существует
RUN if [ ! -f config/__init__.py ]; then \
        echo "# Config package for CartingBot" > config/__init__.py; \
    fi

# Создаем config/config.py из примера если не существует
RUN if [ ! -f config/config.py ] && [ -f config/config.py.example ]; then \
        cp config/config.py.example config/config.py; \
    fi

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Создаем пользователя для запуска приложения (безопасность)
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Экспонируем порт для webhook'ов (если понадобится)
EXPOSE 8443

# Команда по умолчанию
CMD ["python", "main.py"] 