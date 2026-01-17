import json
import time
import requests
import jwt
from typing import Optional, Dict

IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
AUD = IAM_URL
COMPUTE_START_URL = "https://compute.api.cloud.yandex.net/compute/v1/instances/{instance_id}:start"
COMPUTE_GET_URL = "https://compute.api.cloud.yandex.net/compute/v1/instances/{instance_id}"

class YandexCloudError(Exception):
    """Базовый класс для ошибок Yandex Cloud API"""
    pass

class AuthenticationError(YandexCloudError):
    """Ошибка аутентификации"""
    pass

class InstanceError(YandexCloudError):
    """Ошибка работы с инстансом"""
    pass

def load_sa_key(path: str) -> dict:
    """
    Загружает Service Account ключ из JSON файла.
    
    Args:
        path: путь к файлу с ключом
        
    Returns:
        dict с данными ключа
        
    Raises:
        FileNotFoundError: если файл не найден
        json.JSONDecodeError: если файл не валидный JSON
        KeyError: если в файле нет необходимых полей
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Проверяем наличие необходимых полей
        required_fields = ["service_account_id", "id", "private_key"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise KeyError(f"Missing required fields in SA key: {', '.join(missing)}")
        
        return data
    except FileNotFoundError:
        raise FileNotFoundError(f"SA key file not found: {path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in SA key file: {e.msg}", e.doc, e.pos)

def make_jwt(sa_key: dict) -> str:
    """
    Создаёт JWT токен для Service Account.
    
    SA authorized key json содержит:
      - service_account_id
      - id (key_id)
      - private_key
    JWT алгоритм PS256, далее обмен на IAM token.
    
    Args:
        sa_key: словарь с данными Service Account ключа
        
    Returns:
        JWT токен как строка
    """
    now = int(time.time())
    payload = {
        "aud": AUD,
        "iss": sa_key["service_account_id"],
        "iat": now,
        "exp": now + 360,  # 6 минут
    }
    headers = {"kid": sa_key["id"]}
    
    try:
        token = jwt.encode(
            payload,
            sa_key["private_key"],
            algorithm="PS256",
            headers=headers,
        )
        return token
    except Exception as e:
        raise AuthenticationError(f"Failed to create JWT: {e}")

def get_iam_token(sa_key_path: str) -> str:
    """
    Получает IAM токен для Service Account.
    
    Args:
        sa_key_path: путь к файлу с ключом SA
        
    Returns:
        IAM токен
        
    Raises:
        AuthenticationError: если не удалось получить токен
    """
    try:
        sa_key = load_sa_key(sa_key_path)
        token_jwt = make_jwt(sa_key)

        r = requests.post(
            IAM_URL, 
            json={"jwt": token_jwt}, 
            timeout=15,
            headers={"Content-Type": "application/json"}
        )
        r.raise_for_status()
        data = r.json()
        
        if "iamToken" not in data:
            raise AuthenticationError("No iamToken in response")
        
        return data["iamToken"]
    except requests.exceptions.Timeout:
        raise AuthenticationError("IAM API timeout")
    except requests.exceptions.ConnectionError:
        raise AuthenticationError("Cannot connect to IAM API")
    except requests.exceptions.HTTPError as e:
        raise AuthenticationError(f"IAM API HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        if isinstance(e, (AuthenticationError, FileNotFoundError, json.JSONDecodeError, KeyError)):
            raise
        raise AuthenticationError(f"Unexpected error getting IAM token: {e}")

def get_instance_status(instance_id: str, iam_token: str) -> Optional[str]:
    """
    Получает статус VM.
    
    Args:
        instance_id: ID инстанса
        iam_token: IAM токен
        
    Returns:
        Статус VM (RUNNING, STOPPED, STARTING, etc.) или None при ошибке
    """
    try:
        url = COMPUTE_GET_URL.format(instance_id=instance_id)
        headers = {"Authorization": f"Bearer {iam_token}"}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("status", None)
    except Exception as e:
        print(f"[yc_api] Failed to get instance status: {e}")
        return None

def start_instance(instance_id: str, iam_token: str, check_status: bool = True) -> Dict[str, any]:
    """
    Запускает VM в Yandex Cloud.
    
    Args:
        instance_id: ID инстанса
        iam_token: IAM токен
        check_status: проверять ли статус перед запуском
        
    Returns:
        dict с результатом операции: {"success": bool, "message": str, "status": str}
        
    Raises:
        InstanceError: при критической ошибке запуска
    """
    result = {"success": False, "message": "", "status": "unknown"}
    
    try:
        # Проверяем текущий статус
        if check_status:
            current_status = get_instance_status(instance_id, iam_token)
            result["status"] = current_status or "unknown"
            
            if current_status == "RUNNING":
                result["success"] = True
                result["message"] = "Instance already running"
                return result
            elif current_status == "STARTING":
                result["success"] = True
                result["message"] = "Instance already starting"
                return result
        
        # Пытаемся запустить
        url = COMPUTE_START_URL.format(instance_id=instance_id)
        headers = {"Authorization": f"Bearer {iam_token}"}
        r = requests.post(url, headers=headers, timeout=30)
        
        # 200/202 — успех
        if r.status_code in (200, 202):
            result["success"] = True
            result["message"] = "Start command sent successfully"
            result["status"] = "STARTING"
            return result
        
        # 409 — уже запущен
        if r.status_code == 409:
            result["success"] = True
            result["message"] = "Instance already running (409)"
            result["status"] = "RUNNING"
            return result
        
        # Другие ошибки
        error_text = r.text
        result["message"] = f"Start failed with status {r.status_code}: {error_text}"
        raise InstanceError(result["message"])
        
    except requests.exceptions.Timeout:
        result["message"] = "Compute API timeout"
        raise InstanceError(result["message"])
    except requests.exceptions.ConnectionError:
        result["message"] = "Cannot connect to Compute API"
        raise InstanceError(result["message"])
    except InstanceError:
        raise
    except Exception as e:
        result["message"] = f"Unexpected error starting instance: {e}"
        raise InstanceError(result["message"])
