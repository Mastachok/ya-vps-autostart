FROM python:3.11-slim

# Метаданные
LABEL maintainer="VPS Watchdog"
LABEL version="3.0.0"
LABEL description="Multi-VM monitoring with Telegram notifications"

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    iputils-ping \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir \
    yandexcloud==0.307.0 \
    requests==2.31.0 \
    grpcio==1.60.0 \
    protobuf==4.25.1

# Создаём рабочую директорию
WORKDIR /app

# Копируем приложение
COPY app/*.py /app/

# Создаём директории
RUN mkdir -p /app/config /app/profiles /app/data /app/logs

# Запускаем мониторинг
CMD ["python", "-u", "monitor.py"]
