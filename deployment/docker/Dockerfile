# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    sudo \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем только нужные файлы и директории
COPY main.py .
COPY src/ src/
COPY config/ config/
COPY utils/ utils/

# Копируем и делаем исполняемым entrypoint скрипт
COPY deployment/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

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

# Создаем директории для логов и базы данных с максимальными правами
RUN mkdir -p logs data config

# Устанавливаем максимальные права для ВСЕХ файлов и директорий
RUN chmod -R 777 /app
RUN chmod -R 777 logs data config
RUN find /app -type f -name "*.py" -exec chmod 777 {} \;
RUN find /app -type f -name "*.sh" -exec chmod 777 {} \;

# Делаем все скрипты исполняемыми
RUN chmod +x /app/utils/*.py 2>/dev/null || true
RUN chmod +x /app/main.py 2>/dev/null || true

# Экспонируем порт для webhook'ов (если понадобится)
EXPOSE 8443

# Устанавливаем entrypoint
ENTRYPOINT ["/entrypoint.sh"] 