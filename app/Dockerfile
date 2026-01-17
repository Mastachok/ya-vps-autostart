FROM python:3.12-slim

WORKDIR /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir requests PyJWT[crypto] cryptography

# Устанавливаем системные пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends iputils-ping ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Копируем скрипт
COPY monitor.py .
RUN chmod +x monitor.py

# Создаём непривилегированного пользователя
RUN useradd -m -u 1000 watchdog && \
    chown -R watchdog:watchdog /app

USER watchdog

CMD ["python3", "-u", "monitor.py"]
