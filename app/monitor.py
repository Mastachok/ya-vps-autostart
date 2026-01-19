"""
VPS Watchdog v3.0 - Multi-threaded VM Monitor
Многопоточный мониторинг множества VM с Telegram уведомлениями
Использует Service Account ключ
"""

import os
import sys
import time
import json
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Добавляем путь для импорта модулей
sys.path.insert(0, '/opt/vps-watchdog/app')

from vm_manager import VMProfileManager, VMProfile
from telegram_bot import TelegramBot

# Yandex Cloud SDK
try:
    import yandexcloud
    from yandex.cloud.compute.v1.instance_service_pb2 import StartInstanceRequest, GetInstanceRequest
    from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
except ImportError:
    print("ERROR: yandexcloud library not installed")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/watchdog.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class VMMonitor:
    """Монитор для одной VM"""
    
    def __init__(self, profile: VMProfile, sa_key: dict, telegram: TelegramBot):
        self.profile = profile
        self.sa_key = sa_key
        self.telegram = telegram
        self.running = False
        self.thread = None
        
        # Статистика
        self.last_check = None
        self.last_up = None
        self.last_down = None
        self.start_attempts = 0
        self.last_cooldown = None
        self.restarts_count = 0
        
        # Yandex Cloud SDK
        self.sdk = None
        self._init_sdk()
        
    def _init_sdk(self):
        """Инициализация Yandex Cloud SDK"""
        try:
            self.sdk = yandexcloud.SDK(service_account_key=self.sa_key)
            logger.info(f"[{self.profile.name}] SDK инициализирован")
        except Exception as e:
            logger.error(f"[{self.profile.name}] Ошибка инициализации SDK: {e}")
            self.sdk = None
    
    def ping_vm(self) -> bool:
        """Проверка доступности VM через ping"""
        try:
            result = subprocess.run(
                ['ping', '-c', str(self.profile.ping_count), 
                 '-W', str(self.profile.ping_timeout), self.profile.vm_host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.profile.ping_timeout * self.profile.ping_count + 5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"[{self.profile.name}] Ошибка ping: {e}")
            return False
    
    def get_instance_status(self) -> Optional[str]:
        """Получить статус VM из Yandex Cloud"""
        if not self.sdk:
            return None
        try:
            instance_service = self.sdk.client(InstanceServiceStub)
            request = GetInstanceRequest(instance_id=self.profile.instance_id)
            instance = instance_service.Get(request)
            return instance.status
        except Exception as e:
            logger.error(f"[{self.profile.name}] Ошибка получения статуса: {e}")
            return None
    
    def check_operation_in_progress(self) -> bool:
        """Проверка выполнения операций над VM"""
        status = self.get_instance_status()
        if status in ['STARTING', 'STOPPING', 'RESTARTING', 'UPDATING']:
            logger.info(f"[{self.profile.name}] Операция в процессе: {status}")
            return True
        return False
    
    def start_vm(self) -> bool:
        """Запуск VM через Yandex Cloud API"""
        if not self.sdk:
            logger.error(f"[{self.profile.name}] SDK не инициализирован")
            return False
        
        # Проверяем статус перед запуском
        if self.check_operation_in_progress():
            logger.warning(f"[{self.profile.name}] VM занята, ждём...")
            return False
        
        try:
            instance_service = self.sdk.client(InstanceServiceStub)
            
            # Проверяем текущий статус
            status = self.get_instance_status()
            logger.info(f"[{self.profile.name}] Текущий статус: {status}")
            
            if status == 'RUNNING':
                logger.info(f"[{self.profile.name}] VM уже запущена")
                return True
            
            if status == 'STOPPED':
                logger.info(f"[{self.profile.name}] Запуск VM...")
                request = StartInstanceRequest(instance_id=self.profile.instance_id)
                operation = instance_service.Start(request)
                logger.info(f"[{self.profile.name}] Операция запуска: {operation.id}")
                self.restarts_count += 1
                return True
            
            logger.warning(f"[{self.profile.name}] Неожиданный статус: {status}")
            return False
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{self.profile.name}] Ошибка запуска: {error_msg}")
            
            if self.telegram:
                self.telegram.send_message(
                    f"❌ Ошибка запуска VM {self.profile.name}\n"
                    f"💬 {error_msg[:500]}"
                )
            return False
    
    def is_in_cooldown(self) -> bool:
        """Проверка cooldown периода"""
        if not self.last_cooldown:
            return False
        cooldown_end = self.last_cooldown + timedelta(minutes=self.profile.cooldown_minutes)
        return datetime.now() < cooldown_end
    
    def monitor_loop(self):
        """Основной цикл мониторинга"""
        logger.info(f"[{self.profile.name}] Запуск мониторинга")
        logger.info(f"[{self.profile.name}] VM: {self.profile.vm_host}")
        logger.info(f"[{self.profile.name}] Instance ID: {self.profile.instance_id}")
        logger.info(f"[{self.profile.name}] Интервал проверки: {self.profile.check_interval}с")
        
        while self.running:
            try:
                self.last_check = datetime.now()
                
                # Пингуем VM
                is_up = self.ping_vm()
                
                if is_up:
                    # VM доступна
                    if self.last_down:
                        # VM восстановилась
                        downtime = int((datetime.now() - self.last_down).total_seconds())
                        logger.info(f"[{self.profile.name}] ✅ VM восстановлена (downtime: {downtime}с)")
                        if self.telegram:
                            self.telegram.send_message(
                                f"✅ VM {self.profile.name} восстановлена\n"
                                f"🖥️  {self.profile.vm_host}\n"
                                f"⏱️  Downtime: {downtime}с"
                            )
                        self.last_down = None
                        self.start_attempts = 0
                        self.last_cooldown = None
                    else:
                        logger.info(f"[{self.profile.name}] ✅ VM доступна")
                    
                    self.last_up = datetime.now()
                    
                else:
                    # VM недоступна
                    logger.warning(f"[{self.profile.name}] ❌ VM НЕ отвечает (попытка {self.start_attempts + 1})")
                    
                    if not self.last_down:
                        self.last_down = datetime.now()
                    
                    # Проверяем cooldown
                    if self.is_in_cooldown():
                        cooldown_left = int((self.last_cooldown + timedelta(minutes=self.profile.cooldown_minutes) - datetime.now()).total_seconds() / 60)
                        logger.info(f"[{self.profile.name}] ⏳ Cooldown активен, осталось {cooldown_left} минут")
                    else:
                        # Пытаемся запустить
                        if self.start_attempts < self.profile.max_start_attempts:
                            self.start_attempts += 1
                            logger.info(f"[{self.profile.name}] 🔄 Попытка #{self.start_attempts} запустить VM...")
                            
                            # Уведомление о падении
                            if self.telegram:
                                self.telegram.send_message(
                                    f"❌ VM {self.profile.name} не отвечает\n"
                                    f"🖥️  {self.profile.vm_host}\n"
                                    f"🔄 Попытка запуска #{self.start_attempts}"
                                )
                            
                            if self.start_vm():
                                logger.info(f"[{self.profile.name}] 🚀 Команда запуска отправлена")
                                self.last_cooldown = datetime.now()
                            else:
                                logger.error(f"[{self.profile.name}] ❌ Не удалось запустить")
                        else:
                            if not self.last_cooldown or not self.is_in_cooldown():
                                logger.warning(f"[{self.profile.name}] ⚠️ Много попыток подряд, увеличиваю cooldown")
                                self.start_attempts = 0
                                self.last_cooldown = datetime.now()
                
            except Exception as e:
                logger.error(f"[{self.profile.name}] Ошибка в цикле мониторинга: {e}", exc_info=True)
            
            # Ждём перед следующей проверкой
            time.sleep(self.profile.check_interval)
        
        logger.info(f"[{self.profile.name}] Мониторинг остановлен")
    
    def start(self):
        """Запустить мониторинг"""
        if self.running:
            logger.warning(f"[{self.profile.name}] Мониторинг уже запущен")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()
        logger.info(f"[{self.profile.name}] Мониторинг запущен в потоке")
    
    def stop(self):
        """Остановить мониторинг"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"[{self.profile.name}] Мониторинг остановлен")


class MultiVMWatchdog:
    """Главный класс мониторинга множества VM"""
    
    def __init__(self):
        self.profile_manager = VMProfileManager()
        self.telegram = TelegramBot()
        self.monitors = {}
        self.running = False
        
        # Загружаем SA ключ
        self.sa_key_file = os.getenv('SA_KEY_FILE', '/app/config/sa-key.json')
        if not Path(self.sa_key_file).exists():
            logger.error(f"❌ SA ключ не найден: {self.sa_key_file}")
            logger.error(f"📝 Создай SA ключ в Yandex Cloud Console:")
            logger.error(f"   1. IAM → Service accounts → Create")
            logger.error(f"   2. Роли: compute.admin")
            logger.error(f"   3. Create key → JSON")
            logger.error(f"   4. Сохрани как {self.sa_key_file}")
            sys.exit(1)
        
        # Читаем SA ключ
        try:
            with open(self.sa_key_file, 'r') as f:
                self.sa_key = json.load(f)
            logger.info(f"✅ SA ключ загружен")
        except Exception as e:
            logger.error(f"❌ Ошибка чтения SA ключа: {e}")
            sys.exit(1)
        
        logger.info("═" * 80)
        logger.info("🛡️  VPS WATCHDOG v3.0 - Multi-VM Monitor")
        logger.info("═" * 80)
    
    def load_profiles(self):
        """Загрузить и запустить мониторинг для всех включенных профилей"""
        profiles = self.profile_manager.get_enabled_profiles()
        logger.info(f"📊 Найдено активных профилей: {len(profiles)}")
        
        for profile in profiles:
            if profile.id not in self.monitors:
                logger.info(f"➕ Добавляю профиль: {profile.name}")
                logger.info(f"   Instance ID: {profile.instance_id}")
                logger.info(f"   VM Host: {profile.vm_host}")
                logger.info(f"   Folder ID: {profile.folder_id}")
                
                monitor = VMMonitor(profile, self.sa_key, self.telegram)
                self.monitors[profile.id] = monitor
                monitor.start()
    
    def reload_profiles(self):
        """Перезагрузить профили (добавить новые, удалить отключенные)"""
        profiles = self.profile_manager.get_enabled_profiles()
        active_ids = {p.id for p in profiles}
        
        # Останавливаем удалённые/отключенные
        for monitor_id in list(self.monitors.keys()):
            if monitor_id not in active_ids:
                logger.info(f"🗑️  Останавливаю профиль: {self.monitors[monitor_id].profile.name}")
                self.monitors[monitor_id].stop()
                del self.monitors[monitor_id]
        
        # Добавляем новые
        for profile in profiles:
            if profile.id not in self.monitors:
                logger.info(f"➕ Добавляю профиль: {profile.name}")
                monitor = VMMonitor(profile, self.sa_key, self.telegram)
                self.monitors[profile.id] = monitor
                monitor.start()
    
    def run(self):
        """Главный цикл"""
        self.running = True
        self.load_profiles()
        
        if not self.monitors:
            logger.warning("⚠️  Нет активных профилей для мониторинга!")
            logger.info("Добавь профили через меню: sudo vps-watchdog")
            return
        
        logger.info("🚀 Мониторинг запущен!")
        logger.info("=" * 80)
        
        try:
            while self.running:
                time.sleep(60)  # Проверяем новые профили каждую минуту
                self.reload_profiles()
        except KeyboardInterrupt:
            logger.info("\n⚠️  Получен сигнал остановки...")
        finally:
            self.stop()
    
    def stop(self):
        """Остановить все мониторы"""
        logger.info("🛑 Останавливаю все мониторы...")
        for monitor in self.monitors.values():
            monitor.stop()
        logger.info("✅ Все мониторы остановлены")
        self.running = False


if __name__ == '__main__':
    watchdog = MultiVMWatchdog()
    watchdog.run()
