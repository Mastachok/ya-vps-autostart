"""
VPS Watchdog v3.0 - Multi-threaded VM Monitor
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

sys.path.insert(0, '/opt/vps-watchdog/app')

from vm_manager import VMProfileManager, VMProfile
from telegram_bot import TelegramBot

try:
    import yandexcloud
    from yandex.cloud.compute.v1.instance_service_pb2 import StartInstanceRequest, GetInstanceRequest
    from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
except ImportError:
    print("ERROR: yandexcloud library not installed")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/watchdog.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Маппинг статусов VM
VM_STATUS_MAP = {
    0: "STATUS_UNSPECIFIED",
    1: "PROVISIONING",
    2: "RUNNING",
    3: "STOPPING",
    4: "STOPPED",
    5: "STARTING",
    6: "RESTARTING",
    7: "UPDATING",
    8: "ERROR",
    9: "CRASHED",
    10: "DELETING"
}

def get_status_name(status) -> str:
    """Конвертирует числовой статус в строку"""
    if isinstance(status, int):
        return VM_STATUS_MAP.get(status, f"UNKNOWN({status})")
    return str(status)


class VMMonitor:
    """Монитор для одной VM"""
    
    def __init__(self, profile: VMProfile, sa_key: dict, telegram: TelegramBot):
        self.profile = profile
        self.sa_key = sa_key
        self.telegram = telegram
        self.running = False
        self.thread = None
        
        self.last_check = None
        self.last_up = None
        self.last_down = None
        self.start_attempts = 0
        self.last_cooldown = None
        self.restarts_count = 0
        
        self.sdk = None
        self._init_sdk()
        
    def _init_sdk(self):
        """Инициализация SDK"""
        try:
            self.sdk = yandexcloud.SDK(service_account_key=self.sa_key)
            logger.info(f"[{self.profile.name}] SDK инициализирован")
        except Exception as e:
            logger.error(f"[{self.profile.name}] Ошибка SDK: {e}")
            self.sdk = None
    
    def ping_vm(self) -> bool:
        """Ping VM"""
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
        """Получить статус VM"""
        if not self.sdk:
            return None
        try:
            instance_service = self.sdk.client(InstanceServiceStub)
            request = GetInstanceRequest(instance_id=self.profile.instance_id)
            instance = instance_service.Get(request)
            return get_status_name(instance.status)
        except Exception as e:
            logger.error(f"[{self.profile.name}] Ошибка статуса: {e}")
            return None
    
    def check_operation_in_progress(self) -> bool:
        """Проверка операций"""
        status = self.get_instance_status()
        if status in ['STARTING', 'STOPPING', 'RESTARTING', 'UPDATING']:
            logger.info(f"[{self.profile.name}] Операция в процессе: {status}")
            return True
        return False
    
    def start_vm(self) -> bool:
        """Запуск VM"""
        if not self.sdk:
            logger.error(f"[{self.profile.name}] SDK не инициализирован")
            return False
        
        if self.check_operation_in_progress():
            logger.warning(f"[{self.profile.name}] VM занята")
            return False
        
        try:
            instance_service = self.sdk.client(InstanceServiceStub)
            status = self.get_instance_status()
            logger.info(f"[{self.profile.name}] Текущий статус: {status}")
            
            if status == 'RUNNING':
                logger.info(f"[{self.profile.name}] VM уже запущена")
                return True
            
            if status == 'STOPPED':
                logger.info(f"[{self.profile.name}] Запуск VM...")
                request = StartInstanceRequest(instance_id=self.profile.instance_id)
                operation = instance_service.Start(request)
                logger.info(f"[{self.profile.name}] Операция: {operation.id}")
                self.restarts_count += 1
                return True
            
            logger.warning(f"[{self.profile.name}] Неожиданный статус: {status}")
            return False
            
        except Exception as e:
            logger.error(f"[{self.profile.name}] Ошибка запуска: {e}")
            if self.telegram:
                self.telegram.send_message(f"❌ Ошибка запуска {self.profile.name}\n{str(e)[:500]}")
            return False
    
    def is_in_cooldown(self) -> bool:
        """Проверка cooldown"""
        if not self.last_cooldown:
            return False
        cooldown_end = self.last_cooldown + timedelta(minutes=self.profile.cooldown_minutes)
        return datetime.now() < cooldown_end
    
    def monitor_loop(self):
        """Основной цикл мониторинга"""
        logger.info(f"[{self.profile.name}] Запуск мониторинга")
        logger.info(f"[{self.profile.name}] VM: {self.profile.vm_host}")
        logger.info(f"[{self.profile.name}] Instance ID: {self.profile.instance_id}")
        logger.info(f"[{self.profile.name}] Интервал: {self.profile.check_interval}с")
        
        while self.running:
            try:
                self.last_check = datetime.now()
                is_up = self.ping_vm()
                
                if is_up:
                    if self.last_down:
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
                    logger.warning(f"[{self.profile.name}] ❌ VM не отвечает (попытка {self.start_attempts + 1})")
                    
                    if not self.last_down:
                        self.last_down = datetime.now()
                    
                    if self.is_in_cooldown():
                        cooldown_left = int((self.last_cooldown + timedelta(minutes=self.profile.cooldown_minutes) - datetime.now()).total_seconds() / 60)
                        logger.info(f"[{self.profile.name}] ⏳ Cooldown: {cooldown_left} мин")
                    else:
                        if self.start_attempts < self.profile.max_start_attempts:
                            self.start_attempts += 1
                            logger.info(f"[{self.profile.name}] 🔄 Попытка #{self.start_attempts}")
                            
                            if self.telegram:
                                self.telegram.send_message(
                                    f"❌ VM {self.profile.name} не отвечает\n"
                                    f"🖥️  {self.profile.vm_host}\n"
                                    f"🔄 Попытка #{self.start_attempts}"
                                )
                            
                            if self.start_vm():
                                logger.info(f"[{self.profile.name}] 🚀 Команда отправлена")
                                self.last_cooldown = datetime.now()
                            else:
                                logger.error(f"[{self.profile.name}] ❌ Не удалось запустить")
                        else:
                            if not self.last_cooldown or not self.is_in_cooldown():
                                logger.warning(f"[{self.profile.name}] ⚠️ Много попыток")
                                self.start_attempts = 0
                                self.last_cooldown = datetime.now()
                
            except Exception as e:
                logger.error(f"[{self.profile.name}] Ошибка: {e}", exc_info=True)
            
            time.sleep(self.profile.check_interval)
        
        logger.info(f"[{self.profile.name}] Мониторинг остановлен")
    
    def start(self):
        """Запустить мониторинг"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Остановить мониторинг"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


class MultiVMWatchdog:
    """Главный класс"""
    
    def __init__(self):
        self.profile_manager = VMProfileManager()
        self.telegram = TelegramBot()
        self.monitors = {}
        self.running = False
        
        self.sa_key_file = os.getenv('SA_KEY_FILE', '/app/config/sa-key.json')
        if not Path(self.sa_key_file).exists():
            logger.error(f"❌ SA ключ не найден: {self.sa_key_file}")
            sys.exit(1)
        
        try:
            with open(self.sa_key_file, 'r') as f:
                self.sa_key = json.load(f)
            logger.info(f"✅ SA ключ загружен")
        except Exception as e:
            logger.error(f"❌ Ошибка SA ключа: {e}")
            sys.exit(1)
        
        logger.info("═" * 80)
        logger.info("🛡️  VPS WATCHDOG v3.0 - Multi-VM Monitor")
        logger.info("═" * 80)
    
    def load_profiles(self):
        """Загрузить профили"""
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
        """Перезагрузить профили"""
        profiles = self.profile_manager.get_enabled_profiles()
        active_ids = {p.id for p in profiles}
        
        for monitor_id in list(self.monitors.keys()):
            if monitor_id not in active_ids:
                logger.info(f"🗑️  Останавливаю: {self.monitors[monitor_id].profile.name}")
                self.monitors[monitor_id].stop()
                del self.monitors[monitor_id]
        
        for profile in profiles:
            if profile.id not in self.monitors:
                logger.info(f"➕ Добавляю: {profile.name}")
                monitor = VMMonitor(profile, self.sa_key, self.telegram)
                self.monitors[profile.id] = monitor
                monitor.start()
    
    def run(self):
        """Главный цикл"""
        self.running = True
        self.load_profiles()
        
        if not self.monitors:
            logger.warning("⚠️  Нет профилей!")
            return
        
        logger.info("🚀 Мониторинг запущен!")
        logger.info("=" * 80)
        
        try:
            while self.running:
                time.sleep(60)
                self.reload_profiles()
        except KeyboardInterrupt:
            logger.info("\n⚠️  Остановка...")
        finally:
            self.stop()
    
    def stop(self):
        """Остановить"""
        logger.info("🛑 Останавливаю...")
        for monitor in self.monitors.values():
            monitor.stop()
        logger.info("✅ Остановлено")
        self.running = False


if __name__ == '__main__':
    watchdog = MultiVMWatchdog()
    watchdog.run()
