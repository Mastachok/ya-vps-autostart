FROM python:3.12-slim

WORKDIR /app

# Обновляем pip
RUN pip install --no-cache-dir --upgrade pip

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем системные пакеты
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    iputils-ping \
    ca-certificates \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

# Устанавливаем часовой пояс (по умолчанию UTC)
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Копируем Python скрипты
COPY monitor.py yc_api.py ./

# Создаём непривилегированного пользователя для безопасности
RUN useradd -m -u 1000 watchdog && \
    chown -R watchdog:watchdog /app

USER watchdog

# Запускаем с unbuffered output для правильного логирования
CMD ["python", "-u", "monitor.py"]
