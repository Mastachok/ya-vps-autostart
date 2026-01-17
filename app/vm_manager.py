"""
VPS Watchdog v3.0 - VM Profile Manager
Управление профилями виртуальных машин
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class VMProfile:
    """Профиль виртуальной машины"""
    
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name = data.get('name', 'Unnamed VM')
        self.vm_host = data.get('vm_host', '')
        self.instance_id = data.get('instance_id', '')
        self.folder_id = data.get('folder_id', '')
        self.enabled = data.get('enabled', True)
        self.check_interval = data.get('check_interval', 60)
        self.ping_count = data.get('ping_count', 3)
        self.ping_timeout = data.get('ping_timeout', 5)
        self.cooldown_minutes = data.get('cooldown_minutes', 5)
        self.max_start_attempts = data.get('max_start_attempts', 3)
        self.created_at = data.get('created_at', datetime.now().isoformat())
        self.updated_at = data.get('updated_at', datetime.now().isoformat())
        
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'vm_host': self.vm_host,
            'instance_id': self.instance_id,
            'folder_id': self.folder_id,
            'enabled': self.enabled,
            'check_interval': self.check_interval,
            'ping_count': self.ping_count,
            'ping_timeout': self.ping_timeout,
            'cooldown_minutes': self.cooldown_minutes,
            'max_start_attempts': self.max_start_attempts,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def validate(self) -> tuple[bool, str]:
        """Валидация профиля"""
        if not self.vm_host:
            return False, "VM Host не указан"
        if not self.instance_id:
            return False, "Instance ID не указан"
        if not self.folder_id:
            return False, "Folder ID не указан"
        return True, "OK"


class VMProfileManager:
    """Менеджер профилей VM"""
    
    def __init__(self, profiles_dir: str = "/opt/vps-watchdog/profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
    def list_profiles(self) -> List[VMProfile]:
        """Получить список всех профилей"""
        profiles = []
        for file in self.profiles_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    profiles.append(VMProfile(data))
            except Exception as e:
                print(f"Ошибка чтения {file}: {e}")
        return profiles
    
    def get_profile(self, profile_id: str) -> Optional[VMProfile]:
        """Получить профиль по ID"""
        file_path = self.profiles_dir / f"{profile_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return VMProfile(data)
        except Exception as e:
            print(f"Ошибка чтения профиля {profile_id}: {e}")
            return None
    
    def save_profile(self, profile: VMProfile) -> bool:
        """Сохранить профиль"""
        try:
            profile.updated_at = datetime.now().isoformat()
            file_path = self.profiles_dir / f"{profile.id}.json"
            with open(file_path, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения профиля: {e}")
            return False
    
    def delete_profile(self, profile_id: str) -> bool:
        """Удалить профиль"""
        try:
            file_path = self.profiles_dir / f"{profile_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"Ошибка удаления профиля: {e}")
            return False
    
    def create_profile(self, name: str, vm_host: str, instance_id: str, 
                      folder_id: str) -> Optional[VMProfile]:
        """Создать новый профиль"""
        import uuid
        profile_id = str(uuid.uuid4())[:8]
        
        data = {
            'id': profile_id,
            'name': name,
            'vm_host': vm_host,
            'instance_id': instance_id,
            'folder_id': folder_id,
            'enabled': True,
            'created_at': datetime.now().isoformat()
        }
        
        profile = VMProfile(data)
        valid, msg = profile.validate()
        if not valid:
            print(f"Ошибка валидации: {msg}")
            return None
        
        if self.save_profile(profile):
            return profile
        return None
    
    def get_enabled_profiles(self) -> List[VMProfile]:
        """Получить только включенные профили"""
        return [p for p in self.list_profiles() if p.enabled]
    
    def count_profiles(self) -> tuple[int, int]:
        """Подсчитать профили (всего, включенных)"""
        profiles = self.list_profiles()
        total = len(profiles)
        enabled = len([p for p in profiles if p.enabled])
        return total, enabled
