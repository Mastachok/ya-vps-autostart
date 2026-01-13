import json
import time
import requests
import jwt

IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
AUD = IAM_URL
COMPUTE_START_URL = "https://compute.api.cloud.yandex.net/compute/v1/instances/{instance_id}:start"

def load_sa_key(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def make_jwt(sa_key: dict) -> str:
    """
    SA authorized key json содержит:
      - service_account_id
      - id (key_id)
      - private_key
    JWT алгоритм PS256, далее обмен на IAM token.
    """
    now = int(time.time())
    payload = {
        "aud": AUD,
        "iss": sa_key["service_account_id"],
        "iat": now,
        "exp": now + 360,  # 6 минут
    }
    headers = {"kid": sa_key["id"]}
    token = jwt.encode(
        payload,
        sa_key["private_key"],
        algorithm="PS256",
        headers=headers,
    )
    return token

def get_iam_token(sa_key_path: str) -> str:
    sa_key = load_sa_key(sa_key_path)
    token_jwt = make_jwt(sa_key)

    r = requests.post(IAM_URL, json={"jwt": token_jwt}, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data["iamToken"]

def start_instance(instance_id: str, iam_token: str) -> None:
    url = COMPUTE_START_URL.format(instance_id=instance_id)
    headers = {"Authorization": f"Bearer {iam_token}"}
    r = requests.post(url, headers=headers, timeout=30)
    # 200/202 — ок, ошибки иногда бывают "already started" — их просто логируем
    if r.status_code >= 300:
        raise RuntimeError(f"Start failed {r.status_code}: {r.text}")
