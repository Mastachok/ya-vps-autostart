"""
VPS Watchdog v3.0 - Multi-threaded VM Monitor with OAuth support
Многопоточный мониторинг множества VM с Telegram уведомлениями
Использует OAuth токены из профилей вместо Service Account
"""

import os
import sys
import time
import logging
import subprocess
import threading
import requests
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
    
    def __init__(self, profile: VMProfile, oauth_token: Optional[str], telegram: TelegramBot):
        self.profile = profile
        self.oauth_token = oauth_token
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
        self.iam_token = None
        self._init_sdk()
        
    def _get_iam_token(self) -> Optional[str]:
        """Получить IAM токен из OAuth токена с кэшированием"""
        if not self.oauth_token:
            return None
        
        # Проверяем валидность текущего IAM токена (если есть)
        # IAM токены живут 12 часов, поэтому обновляем если прошло больше 11 часов
        if self.iam_token:
            # В продакшене здесь должна быть проверка времени создания токена
            # Для упрощения просто возвращаем существующий
            return self.iam_token
            
        try:
            response = requests.post(
                'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                json={'yandexPassportOauthToken': self.oauth_token},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.iam_token = data.get('iamToken')
                logger.info(f"[{self.profile.name}] IAM токен получен")
                return self.iam_token
            else:
                logger.error(f"[{self.profile.name}] Ошибка получения IAM: {response.text}")
                return None
        except Exception as e:
            logger.error(f"[{self.profile.name}] Ошибка запроса IAM: {e}")
            return None
    
    def _refresh_iam_token(self) -> bool:
        """Принудительное обновление IAM токена"""
        self.iam_token = None  # Сбрасываем текущий
        new_token = self._get_iam_token()
        if new_token:
            # Пересоздаём SDK с новым токеном
            self._init_sdk()
            return True
        return False
    
    def _init_sdk(self):
        """Инициализация Yandex Cloud SDK с OAuth"""
        try:
            # Получаем IAM токен из OAuth
            iam_token = self._get_iam_token()
            if not iam_token:
                logger.warning(f"[{self.profile.name}] Не удалось получить IAM токен, SDK не инициализирован")
                self.sdk = None
                return
            
            # Инициализируем SDK с IAM токеном
            self.sdk = yandexcloud.SDK(iam_token=iam_token)
            logger.info(f"[{self.profile.name}] SDK инициализирован через OAuth")
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
            
            # Проверяем, не истёк ли IAM токен
            if 'UNAUTHENTICATED' in error_msg or 'Unauthorized' in error_msg:
                logger.warning(f"[{self.profile.name}] IAM токен истёк, обновляю...")
                if self._refresh_iam_token():
                    logger.info(f"[{self.profile.name}] IAM токен обновлён, повторяю попытку...")
                    # Рекурсивно повторяем попытку один раз
                    try:
                        return self.start_vm()
                    except:
                        pass
            
            # Отправляем уведомление в Telegram
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
        
        logger.info("═" * 80)
        logger.info("🛡️  VPS WATCHDOG v3.0 - Multi-VM Monitor (OAuth)")
        logger.info("═" * 80)
    
    def _get_oauth_token_for_folder(self, folder_id: str) -> Optional[str]:
        """Получить OAuth токен для конкретной папки из окружения"""
        # Можно передать токен через переменную окружения
        oauth_token = os.getenv('YANDEX_OAUTH_TOKEN')
        if oauth_token:
            logger.info(f"Используется OAuth токен из переменной окружения")
            return oauth_token
        
        # Или читаем из файла конфигурации
        oauth_file = os.getenv('OAUTH_TOKEN_FILE', '/app/config/oauth-token.txt')
        if Path(oauth_file).exists():
            try:
                with open(oauth_file, 'r') as f:
                    token = f.read().strip()
                    logger.info(f"OAuth токен загружен из {oauth_file}")
                    return token
            except Exception as e:
                logger.error(f"Ошибка чтения OAuth токена: {e}")
        
        logger.warning("OAuth токен не найден. Мониторинг будет работать только с ping")
        return None
    
    def load_profiles(self):
        """Загрузить и запустить мониторинг для всех включенных профилей"""
        profiles = self.profile_manager.get_enabled_profiles()
        logger.info(f"📊 Найдено активных профилей: {len(profiles)}")
        
        # Получаем OAuth токен (один для всех профилей)
        oauth_token = self._get_oauth_token_for_folder(None)
        
        for profile in profiles:
            if profile.id not in self.monitors:
                logger.info(f"➕ Добавляю профиль: {profile.name}")
                logger.info(f"   Instance ID: {profile.instance_id}")
                logger.info(f"   VM Host: {profile.vm_host}")
                logger.info(f"   Folder ID: {profile.folder_id}")
                
                monitor = VMMonitor(profile, oauth_token, self.telegram)
                self.monitors[profile.id] = monitor
                monitor.start()
    
    def reload_profiles(self):
        """Перезагрузить профили (добавить новые, удалить отключенные)"""
        profiles = self.profile_manager.get_enabled_profiles()
        active_ids = {p.id for p in profiles}
        oauth_token = self._get_oauth_token_for_folder(None)
        
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
                monitor = VMMonitor(profile, oauth_token, self.telegram)
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
