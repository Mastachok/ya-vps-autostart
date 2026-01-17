import os
import time
import subprocess
import logging
import sys
from datetime import datetime
from typing import Optional
from yc_api import get_iam_token, start_instance, YandexCloudError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

def env_int(name: str, default: int) -> int:
    """Безопасно получает целое число из переменной окружения"""
    try:
        value = os.getenv(name)
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid value for {name}, using default {default}: {e}")
        return default

def env_str(name: str, default: str = "") -> str:
    """Безопасно получает строку из переменной окружения"""
    return os.getenv(name, default).strip()

def ping_ok(host: str, attempts: int, timeout: int) -> bool:
    """
    Проверяет доступность хоста через ping.
    
    Args:
        host: адрес хоста
        attempts: количество попыток
        timeout: таймаут в секундах
        
    Returns:
        True если хост отвечает, False иначе
    """
    if not host:
        logger.error("Host is empty, cannot ping")
        return False
    
    try:
        cmd = ["ping", "-c", str(attempts), "-W", str(timeout), host]
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout * attempts + 10  # Дополнительное время для завершения
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning(f"Ping command timeout for {host}")
        return False
    except FileNotFoundError:
        logger.error("ping command not found in system")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during ping: {e}")
        return False

def validate_config(host: str, instance_id: str, sa_key_file: str) -> bool:
    """
    Проверяет корректность конфигурации.
    
    Returns:
        True если конфигурация валидна, False иначе
    """
    errors = []
    
    if not host:
        errors.append("VM_HOST is not set")
    
    if not instance_id:
        errors.append("INSTANCE_ID is not set")
    
    if not sa_key_file:
        errors.append("SA_KEY_FILE is not set")
    elif not os.path.exists(sa_key_file):
        errors.append(f"SA_KEY_FILE does not exist: {sa_key_file}")
    elif os.path.getsize(sa_key_file) == 0:
        errors.append(f"SA_KEY_FILE is empty: {sa_key_file}")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return False
    
    return True

def main():
    """Основной цикл мониторинга"""
    # Загружаем конфигурацию
    profile = env_str("PROFILE_NAME", "unknown")
    host = env_str("VM_HOST")
    instance_id = env_str("INSTANCE_ID")
    sa_key_file = env_str("SA_KEY_FILE")
    interval = env_int("CHECK_INTERVAL", 60)
    attempts = env_int("PING_ATTEMPTS", 5)
    timeout = env_int("PING_TIMEOUT", 5)
    cooldown_minutes = env_int("COOLDOWN_MINUTES", 5)
    
    # Валидация параметров
    if interval < 10:
        logger.warning(f"CHECK_INTERVAL too small ({interval}s), setting to 10s")
        interval = 10
    
    if cooldown_minutes < 1:
        logger.warning(f"COOLDOWN_MINUTES too small ({cooldown_minutes}), setting to 1")
        cooldown_minutes = 1
    
    cooldown_seconds = cooldown_minutes * 60
    
    # Логируем конфигурацию
    logger.info("=" * 60)
    logger.info("VPS Watchdog starting")
    logger.info("=" * 60)
    logger.info(f"Profile: {profile}")
    logger.info(f"VM Host: {host}")
    logger.info(f"Instance ID: {instance_id}")
    logger.info(f"SA Key File: {sa_key_file}")
    logger.info(f"Check Interval: {interval}s")
    logger.info(f"Ping Attempts: {attempts}")
    logger.info(f"Ping Timeout: {timeout}s")
    logger.info(f"Cooldown: {cooldown_minutes} minutes ({cooldown_seconds}s)")
    logger.info("=" * 60)
    
    # Валидация конфигурации
    if not validate_config(host, instance_id, sa_key_file):
        logger.error("Invalid configuration. Please check your .env file and SA key.")
        logger.error("Watchdog will sleep indefinitely. Fix the configuration and restart the container.")
        while True:
            time.sleep(3600)  # Спим по часу
    
    logger.info("Configuration valid, starting monitoring loop")
    
    cooldown_until = 0
    consecutive_failures = 0
    last_start_attempt = 0
    
    while True:
        try:
            # Проверяем доступность
            is_alive = ping_ok(host, attempts, timeout)
            now = time.time()
            
            if is_alive:
                if consecutive_failures > 0:
                    logger.info(f"✅ VM {host} is UP (was down {consecutive_failures} times)")
                    consecutive_failures = 0
                else:
                    logger.info(f"✅ VM {host} is UP")
            else:
                consecutive_failures += 1
                logger.warning(f"❌ VM {host} is DOWN (attempt {consecutive_failures})")
                
                # Проверяем cooldown
                if now < cooldown_until:
                    remaining = int(cooldown_until - now)
                    logger.info(f"⏳ Cooldown active, {remaining}s remaining until next start attempt")
                else:
                    # Пытаемся запустить
                    logger.info(f"🚀 Attempting to start instance {instance_id}")
                    last_start_attempt = now
                    
                    try:
                        # Получаем IAM токен
                        logger.info("Getting IAM token...")
                        iam_token = get_iam_token(sa_key_file)
                        logger.info("IAM token obtained successfully")
                        
                        # Запускаем инстанс
                        logger.info("Sending start command...")
                        result = start_instance(instance_id, iam_token, check_status=True)
                        
                        if result["success"]:
                            logger.info(f"✅ {result['message']} (status: {result.get('status', 'unknown')})")
                        else:
                            logger.error(f"❌ {result['message']}")
                        
                        # Устанавливаем cooldown
                        cooldown_until = now + cooldown_seconds
                        logger.info(f"⏳ Cooldown set for {cooldown_minutes} minutes")
                        
                    except YandexCloudError as e:
                        logger.error(f"❌ Yandex Cloud API error: {e}")
                        cooldown_until = now + cooldown_seconds
                    except Exception as e:
                        logger.error(f"❌ Unexpected error during start: {e}", exc_info=True)
                        cooldown_until = now + cooldown_seconds
            
            # Ждём до следующей проверки
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            logger.info(f"Sleeping {interval}s before retry...")
            time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
