"""
VPS Watchdog v3.0 - Telegram Bot
Полнофункциональный бот для управления и уведомлений
"""

import json
import requests
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram бот для уведомлений и управления"""
    
    def __init__(self, config_file: str = "/opt/vps-watchdog/config/telegram.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.bot_token = self.config.get('bot_token', '')
        self.chat_id = self.config.get('chat_id', '')
        self.enabled = self.config.get('enabled', False)
        
    def _load_config(self) -> dict:
        """Загрузить конфигурацию"""
        if not self.config_file.exists():
            return {
                'bot_token': '',
                'chat_id': '',
                'enabled': False,
                'notify_on_down': True,
                'notify_on_up': True,
                'notify_on_error': True,
                'notify_on_start': False
            }
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки конфига Telegram: {e}")
            return {}
    
    def save_config(self) -> bool:
        """Сохранить конфигурацию"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения конфига: {e}")
            return False
    
    def configure(self, bot_token: str, chat_id: str) -> bool:
        """Настроить бота"""
        self.config['bot_token'] = bot_token
        self.config['chat_id'] = chat_id
        self.config['enabled'] = True
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = True
        return self.save_config()
    
    def is_configured(self) -> bool:
        """Проверка настройки бота"""
        return bool(self.bot_token and self.chat_id and self.enabled)
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Отправить сообщение"""
        if not self.is_configured():
            logger.warning("Telegram не настроен")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False
    
    def notify_vm_down(self, vm_name: str, vm_host: str, attempt: int = 1) -> bool:
        """Уведомление о падении VM"""
        if not self.config.get('notify_on_down', True):
            return False
        
        text = f"""🔴 <b>VM Недоступна!</b>

📊 <b>Профиль:</b> {vm_name}
🌐 <b>IP:</b> <code>{vm_host}</code>
⏰ <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
🔄 <b>Попытка запуска:</b> #{attempt}

⚙️ Запускаю VM через Yandex Cloud API..."""
        
        return self.send_message(text)
    
    def notify_vm_up(self, vm_name: str, vm_host: str, downtime_seconds: int = 0) -> bool:
        """Уведомление о запуске VM"""
        if not self.config.get('notify_on_up', True):
            return False
        
        downtime_str = ""
        if downtime_seconds > 0:
            minutes = downtime_seconds // 60
            seconds = downtime_seconds % 60
            if minutes > 0:
                downtime_str = f"\n⏱️ <b>Downtime:</b> {minutes}м {seconds}с"
            else:
                downtime_str = f"\n⏱️ <b>Downtime:</b> {seconds}с"
        
        text = f"""🟢 <b>VM Восстановлена!</b>

📊 <b>Профиль:</b> {vm_name}
🌐 <b>IP:</b> <code>{vm_host}</code>
⏰ <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}{downtime_str}

✅ VM успешно запущена и отвечает на ping!"""
        
        return self.send_message(text)
    
    def notify_error(self, vm_name: str, vm_host: str, error: str) -> bool:
        """Уведомление об ошибке"""
        if not self.config.get('notify_on_error', True):
            return False
        
        text = f"""⚠️ <b>Ошибка запуска VM!</b>

📊 <b>Профиль:</b> {vm_name}
🌐 <b>IP:</b> <code>{vm_host}</code>
⏰ <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

❌ <b>Ошибка:</b>
<code>{error}</code>

🔄 Повторная попытка через cooldown период..."""
        
        return self.send_message(text)
    
    def send_status(self, profiles_data: list) -> bool:
        """Отправить статус всех VM"""
        if not profiles_data:
            return self.send_message("📊 <b>Нет активных профилей</b>")
        
        text = "🛡️ <b>VPS Watchdog Status</b>\n\n"
        
        for profile in profiles_data:
            status_icon = "🟢" if profile.get('status') == 'online' else "🔴"
            name = profile.get('name', 'Unknown')
            ip = profile.get('vm_host', 'N/A')
            uptime = profile.get('uptime', 'N/A')
            last_check = profile.get('last_check', 'N/A')
            
            text += f"📊 <b>{name}</b>\n"
            text += f"├─ {status_icon} <b>Статус:</b> {profile.get('status', 'unknown')}\n"
            text += f"├─ 🌐 <b>IP:</b> <code>{ip}</code>\n"
            text += f"├─ ⏱️ <b>Uptime:</b> {uptime}\n"
            text += f"└─ ✅ <b>Проверка:</b> {last_check}\n\n"
        
        online = len([p for p in profiles_data if p.get('status') == 'online'])
        offline = len(profiles_data) - online
        
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📈 <b>Всего VM:</b> {len(profiles_data)} | ✅ {online} | ❌ {offline}"
        
        return self.send_message(text)
    
    def send_logs(self, logs: str) -> bool:
        """Отправить логи"""
        if not logs:
            return self.send_message("📜 <b>Логи пусты</b>")
        
        text = f"📜 <b>Последние логи:</b>\n\n<pre>{logs[-3000:]}</pre>"
        return self.send_message(text)
    
    def send_stats(self, stats_data: dict) -> bool:
        """Отправить статистику"""
        text = "📊 <b>Статистика VPS Watchdog</b>\n\n"
        
        for vm_name, data in stats_data.items():
            text += f"📌 <b>{vm_name}</b>\n"
            text += f"├─ ⏱️ <b>Uptime:</b> {data.get('uptime', 'N/A')}\n"
            text += f"├─ ⏸️ <b>Downtime:</b> {data.get('downtime', 'N/A')}\n"
            text += f"├─ 🔄 <b>Рестарты:</b> {data.get('restarts', 0)}\n"
            text += f"└─ 📈 <b>Availability:</b> {data.get('availability', 'N/A')}%\n\n"
        
        return self.send_message(text)
    
    def test_connection(self) -> tuple[bool, str]:
        """Тест подключения к боту"""
        if not self.bot_token:
            return False, "Bot token не указан"
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('ok'):
                bot_name = data.get('result', {}).get('username', 'Unknown')
                return True, f"✅ Бот подключен: @{bot_name}"
            return False, "Неверный ответ API"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
