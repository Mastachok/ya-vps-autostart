#!/usr/bin/env python3
"""
VPS Watchdog v2.0
Простой мониторинг и автозапуск VM в Yandex Cloud
"""

import os
import sys
import time
import json
import subprocess
import logging
from datetime import datetime
from typing import Optional, Dict, Tuple
import requests
import jwt

# ═══════════════════════════════════════════════════════════════════
# ЛОГИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('watchdog')

# ═══════════════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════════════

IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
COMPUTE_URL = "https://compute.api.cloud.yandex.net/compute/v1"

# ═══════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════

class Config:
    """Конфигурация watchdog"""
    
    def __init__(self):
        self.vm_host = self._get_str('VM_HOST')
        self.instance_id = self._get_str('INSTANCE_ID')
        self.sa_key_file = self._get_str('SA_KEY_FILE', '/app/config/sa-key.json')
        
        self.check_interval = self._get_int('CHECK_INTERVAL', 60, 10, 3600)
        self.ping_count = self._get_int('PING_COUNT', 3, 1, 10)
        self.ping_timeout = self._get_int('PING_TIMEOUT', 5, 1, 30)
        self.cooldown_minutes = self._get_int('COOLDOWN_MINUTES', 5, 1, 60)
        self.max_start_attempts = self._get_int('MAX_START_ATTEMPTS', 3, 1, 10)
    
    def _get_str(self, name: str, default: str = '') -> str:
        """Получение строки из env"""
        return os.getenv(name, default).strip()
    
    def _get_int(self, name: str, default: int, min_val: int, max_val: int) -> int:
        """Получение целого числа с валидацией"""
        try:
            value = int(os.getenv(name, default))
            if value < min_val:
                logger.warning(f"{name}={value} too small, using {min_val}")
                return min_val
            if value > max_val:
                logger.warning(f"{name}={value} too large, using {max_val}")
                return max_val
            return value
        except (ValueError, TypeError):
            logger.warning(f"Invalid {name}, using default {default}")
            return default
    
    def validate(self) -> Tuple[bool, list]:
        """Проверка конфигурации"""
        errors = []
        
        if not self.vm_host:
            errors.append("❌ VM_HOST не указан")
        
        if not self.instance_id:
            errors.append("❌ INSTANCE_ID не указан")
        
        if not self.sa_key_file:
            errors.append("❌ SA_KEY_FILE не указан")
        elif not os.path.exists(self.sa_key_file):
            errors.append(f"❌ Файл ключа не найден: {self.sa_key_file}")
        elif os.path.getsize(self.sa_key_file) == 0:
            errors.append(f"❌ Файл ключа пустой: {self.sa_key_file}")
        else:
            # Проверяем валидность JSON
            try:
                with open(self.sa_key_file, 'r') as f:
                    key = json.load(f)
                required = ['service_account_id', 'id', 'private_key']
                missing = [f for f in required if f not in key]
                if missing:
                    errors.append(f"❌ В ключе отсутствуют поля: {', '.join(missing)}")
            except json.JSONDecodeError:
                errors.append("❌ Файл ключа содержит невалидный JSON")
            except Exception as e:
                errors.append(f"❌ Ошибка чтения ключа: {e}")
        
        return (len(errors) == 0, errors)
    
    def print(self):
        """Красивый вывод конфигурации"""
        logger.info("═" * 70)
        logger.info("🛡️  VPS WATCHDOG - Конфигурация")
        logger.info("═" * 70)
        logger.info(f"🌐 VM Host:             {self.vm_host or '<НЕ УКАЗАН>'}")
        logger.info(f"🆔 Instance ID:         {self.instance_id or '<НЕ УКАЗАН>'}")
        logger.info(f"🔑 SA Key:              {self.sa_key_file}")
        logger.info(f"⏱️  Интервал проверки:   {self.check_interval}с")
        logger.info(f"📡 Ping попыток:        {self.ping_count}")
        logger.info(f"⏰ Ping таймаут:        {self.ping_timeout}с")
        logger.info(f"⏳ Cooldown:            {self.cooldown_minutes} минут")
        logger.info(f"🔄 Макс. попыток:       {self.max_start_attempts}")
        logger.info("═" * 70)

# ═══════════════════════════════════════════════════════════════════
# YANDEX CLOUD API
# ═══════════════════════════════════════════════════════════════════

class YandexCloudAPI:
    """Работа с Yandex Cloud API"""
    
    def __init__(self, sa_key_file: str):
        self.sa_key_file = sa_key_file
        self._iam_token: Optional[str] = None
        self._token_expires_at = 0
    
    def _load_sa_key(self) -> dict:
        """Загрузка ключа Service Account"""
        with open(self.sa_key_file, 'r') as f:
            return json.load(f)
    
    def _create_jwt(self, sa_key: dict) -> str:
        """Создание JWT токена"""
        now = int(time.time())
        payload = {
            'aud': IAM_URL,
            'iss': sa_key['service_account_id'],
            'iat': now,
            'exp': now + 360
        }
        headers = {'kid': sa_key['id']}
        return jwt.encode(payload, sa_key['private_key'], algorithm='PS256', headers=headers)
    
    def get_iam_token(self, force: bool = False) -> str:
        """Получение IAM токена (с кешированием)"""
        now = time.time()
        
        if not force and self._iam_token and now < self._token_expires_at:
            return self._iam_token
        
        sa_key = self._load_sa_key()
        jwt_token = self._create_jwt(sa_key)
        
        response = requests.post(IAM_URL, json={'jwt': jwt_token}, timeout=15)
        response.raise_for_status()
        
        self._iam_token = response.json()['iamToken']
        self._token_expires_at = now + 10800  # 3 часа
        
        return self._iam_token
    
    def get_instance_status(self, instance_id: str) -> Optional[str]:
        """Получение статуса VM"""
        try:
            token = self.get_iam_token()
            url = f"{COMPUTE_URL}/instances/{instance_id}"
            response = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
            response.raise_for_status()
            return response.json().get('status')
        except Exception as e:
            logger.error(f"Ошибка получения статуса VM: {e}")
            return None
    
    def start_instance(self, instance_id: str) -> Tuple[bool, str]:
        """Запуск VM"""
        try:
            token = self.get_iam_token()
            url = f"{COMPUTE_URL}/instances/{instance_id}:start"
            response = requests.post(url, headers={'Authorization': f'Bearer {token}'}, timeout=30)
            
            if response.status_code in (200, 202):
                return (True, "VM запускается")
            elif response.status_code == 409:
                return (True, "VM уже запущена")
            else:
                return (False, f"Ошибка {response.status_code}: {response.text}")
        
        except Exception as e:
            return (False, str(e))

# ═══════════════════════════════════════════════════════════════════
# ПРОВЕРКА ДОСТУПНОСТИ
# ═══════════════════════════════════════════════════════════════════

def check_vm_alive(host: str, count: int, timeout: int) -> bool:
    """Проверка доступности VM через ping"""
    try:
        cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout * count + 5)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        logger.error(f"Ошибка ping: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════
# ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════════════

def main():
    """Основной цикл мониторинга"""
    
    # Загружаем конфигурацию
    config = Config()
    config.print()
    
    # Валидация
    is_valid, errors = config.validate()
    if not is_valid:
        logger.error("❌ Ошибки конфигурации:")
        for error in errors:
            logger.error(f"   {error}")
        logger.error("")
        logger.error("💡 Исправь конфигурацию и перезапусти контейнер:")
        logger.error("   sudo vps-watchdog config")
        logger.error("   sudo systemctl restart vps-watchdog")
        logger.error("")
        logger.info("😴 Засыпаю до исправления...")
        while True:
            time.sleep(3600)
    
    logger.info("✅ Конфигурация валидна")
    logger.info("🚀 Запуск мониторинга...\n")
    
    # Инициализация API
    api = YandexCloudAPI(config.sa_key_file)
    
    # Состояние
    cooldown_until = 0
    consecutive_failures = 0
    start_attempts_counter = 0
    last_status = None
    
    # Основной цикл
    while True:
        try:
            now = time.time()
            is_alive = check_vm_alive(config.vm_host, config.ping_count, config.ping_timeout)
            
            if is_alive:
                # VM доступна
                if last_status != 'UP':
                    logger.info(f"✅ VM {config.vm_host} доступна")
                    if consecutive_failures > 0:
                        logger.info(f"   (была недоступна {consecutive_failures} раз)")
                    consecutive_failures = 0
                    start_attempts_counter = 0
                last_status = 'UP'
            
            else:
                # VM недоступна
                consecutive_failures += 1
                logger.warning(f"❌ VM {config.vm_host} НЕ отвечает (попытка {consecutive_failures})")
                
                # Проверяем cooldown
                if now < cooldown_until:
                    remaining = int((cooldown_until - now) / 60)
                    logger.info(f"⏳ Cooldown активен, осталось {remaining} минут")
                
                else:
                    # Пытаемся запустить
                    start_attempts_counter += 1
                    logger.info(f"🚀 Попытка #{start_attempts_counter} запустить VM...")
                    
                    # Проверяем статус
                    status = api.get_instance_status(config.instance_id)
                    if status:
                        logger.info(f"   Текущий статус: {status}")
                        
                        if status == 'RUNNING':
                            logger.warning("   ⚠️  VM показывает статус RUNNING, но не пингуется")
                            logger.warning("   Возможно проблема с сетью внутри VM")
                        elif status == 'STARTING':
                            logger.info("   VM уже запускается, ждём...")
                    
                    # Запускаем
                    success, message = api.start_instance(config.instance_id)
                    if success:
                        logger.info(f"   ✅ {message}")
                    else:
                        logger.error(f"   ❌ {message}")
                    
                    # Устанавливаем cooldown
                    # Если много попыток подряд - увеличиваем cooldown
                    if start_attempts_counter >= config.max_start_attempts:
                        cooldown_mins = config.cooldown_minutes * 2
                        logger.warning(f"   ⚠️  Много попыток подряд, увеличиваю cooldown до {cooldown_mins} минут")
                        start_attempts_counter = 0
                    else:
                        cooldown_mins = config.cooldown_minutes
                    
                    cooldown_until = now + (cooldown_mins * 60)
                    logger.info(f"⏳ Cooldown установлен на {cooldown_mins} минут\n")
                
                last_status = 'DOWN'
            
            # Ждём до следующей проверки
            time.sleep(config.check_interval)
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  Получен сигнал остановки")
            logger.info("👋 Завершение работы...")
            break
        
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            logger.info(f"😴 Сплю {config.check_interval}с и попробую снова...\n")
            time.sleep(config.check_interval)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"💀 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
