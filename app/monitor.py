import os
import time
import subprocess
from yc_api import get_iam_token, start_instance

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def ping_ok(host: str, attempts: int, timeout: int) -> bool:
    # ping -c <attempts> -W <timeout>
    cmd = ["ping", "-c", str(attempts), "-W", str(timeout), host]
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p.returncode == 0

def main():
    profile = os.getenv("PROFILE_NAME", "unknown")
    host = os.getenv("VM_HOST", "")
    instance_id = os.getenv("INSTANCE_ID", "")
    sa_key_file = os.getenv("SA_KEY_FILE", "")
    interval = env_int("CHECK_INTERVAL", 60)
    attempts = env_int("PING_ATTEMPTS", 5)
    timeout = env_int("PING_TIMEOUT", 5)

    print(f"[watchdog] profile={profile} host={host} instance_id={instance_id} interval={interval}s")

    if not host or not instance_id or not sa_key_file:
        print("[watchdog] ERROR: VM_HOST/INSTANCE_ID/SA_KEY_FILE not set in .env")
        while True:
            time.sleep(60)

    cooldown_until = 0

    while True:
        ok = ping_ok(host, attempts, timeout)
        now = time.time()

        if ok:
            print(f"[watchdog] OK ping {host}")
        else:
            print(f"[watchdog] DOWN ping {host}")
            # анти-дребезг: не стартуем чаще чем раз в 5 минут
            if now < cooldown_until:
                print("[watchdog] cooldown, skip start")
            else:
                try:
                    iam = get_iam_token(sa_key_file)
                    start_instance(instance_id, iam)
                    print("[watchdog] start requested")
                except Exception as e:
                    print(f"[watchdog] start error: {e}")
                cooldown_until = now + 300

        time.sleep(interval)

if __name__ == "__main__":
    main()
