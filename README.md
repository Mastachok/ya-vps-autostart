# VPS Watchdog — автозапуск ВМ (Yandex Cloud)

Это утилита, которая:
- пингует вашу ВМ (VM_HOST)
- если ВМ не отвечает — пытается запустить её в Yandex Cloud по INSTANCE_ID
- поддерживает несколько профилей (разные ВМ)

---

## ⚡ Установка (1 команда)

```bash
curl -fsSL https://raw.githubusercontent.com/Mastachok/ya-vps-autostart/main/install.sh | sudo bash
