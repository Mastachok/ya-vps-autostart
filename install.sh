#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# VPS Watchdog v3.0 - Installation Script
# ═══════════════════════════════════════════════════════════════════

VERSION="3.0.0"
INSTALL_DIR="/opt/vps-watchdog"
REPO_URL="https://github.com/Mastachok/ya-vps-autostart"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}       🛡️  VPS WATCHDOG v${VERSION} - Installation${NC}"
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════════${NC}"
echo

# Проверка прав
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ Запусти с правами root${NC}"
    exit 1
fi

# Проверка ОС
if [[ ! -f /etc/os-release ]]; then
    echo -e "${RED}❌ Неподдерживаемая ОС${NC}"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]] && [[ "$ID" != "debian" ]]; then
    echo -e "${YELLOW}⚠️  Поддерживаются только Ubuntu/Debian${NC}"
    echo "Продолжить? (yes/no)"
    read -r confirm
    [[ "$confirm" != "yes" ]] && exit 1
fi

# Проверка Docker
echo -e "${CYAN}🔍 Проверка Docker...${NC}"
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${YELLOW}Docker не установлен, устанавливаю...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}✅ Docker установлен${NC}"
else
    echo -e "${GREEN}✅ Docker найден${NC}"
fi

# Проверка Docker Compose
if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${YELLOW}Docker Compose не установлен, устанавливаю...${NC}"
    apt-get update -qq
    apt-get install -y docker-compose
    echo -e "${GREEN}✅ Docker Compose установлен${NC}"
else
    echo -e "${GREEN}✅ Docker Compose найден${NC}"
fi

# Проверка jq
if ! command -v jq >/dev/null 2>&1; then
    echo -e "${YELLOW}jq не установлен, устанавливаю...${NC}"
    apt-get update -qq
    apt-get install -y jq
    echo -e "${GREEN}✅ jq установлен${NC}"
else
    echo -e "${GREEN}✅ jq найден${NC}"
fi

# Миграция с v2.0
if [[ -d "$INSTALL_DIR" ]] && [[ ! -d "$INSTALL_DIR/profiles" ]]; then
    echo
    echo -e "${CYAN}📦 Обнаружена версия 2.0, выполняю миграцию...${NC}"
    
    # Создаём директорию профилей
    mkdir -p "$INSTALL_DIR/profiles"
    
    # Если есть старый конфиг - создаём профиль из него
    if [[ -f "$INSTALL_DIR/config/watchdog.env" ]]; then
        source "$INSTALL_DIR/config/watchdog.env" 2>/dev/null || true
        
        if [[ -n "${VM_HOST:-}" ]] && [[ -n "${INSTANCE_ID:-}" ]]; then
            profile_id=$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
            
            cat > "$INSTALL_DIR/profiles/${profile_id}.json" <<EOF
{
  "id": "$profile_id",
  "name": "Migrated from v2.0",
  "vm_host": "$VM_HOST",
  "instance_id": "$INSTANCE_ID",
  "folder_id": "${FOLDER_ID:-}",
  "enabled": true,
  "check_interval": ${CHECK_INTERVAL:-60},
  "ping_count": ${PING_COUNT:-3},
  "ping_timeout": ${PING_TIMEOUT:-5},
  "cooldown_minutes": ${COOLDOWN_MINUTES:-5},
  "max_start_attempts": ${MAX_START_ATTEMPTS:-3},
  "created_at": "$(date -Iseconds)",
  "updated_at": "$(date -Iseconds)"
}
EOF
            echo -e "${GREEN}✅ Создан профиль из старой конфигурации${NC}"
        fi
    fi
    
    # Бэкап старой версии
    if [[ -d "$INSTALL_DIR.v2-backup" ]]; then
        rm -rf "$INSTALL_DIR.v2-backup"
    fi
    cp -r "$INSTALL_DIR" "$INSTALL_DIR.v2-backup"
    echo -e "${GREEN}✅ Бэкап v2.0 создан: $INSTALL_DIR.v2-backup${NC}"
fi

# Установка
echo
echo -e "${CYAN}📥 Установка VPS Watchdog v${VERSION}...${NC}"

# Создаём директории
mkdir -p "$INSTALL_DIR"/{app,bin,config,profiles,data,logs,docs}

# Скачиваем файлы
echo "Скачиваю файлы..."

# Если установка из локальной директории (для разработки)
if [[ -d "/home/claude/vps-watchdog-v3" ]]; then
    echo "Копирую из локальной директории..."
    cp -r /home/claude/vps-watchdog-v3/* "$INSTALL_DIR/"
else
    # Скачиваем из GitHub
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    curl -fsSL "${REPO_URL}/archive/refs/heads/main.tar.gz" -o repo.tar.gz
    tar -xzf repo.tar.gz --strip-components=1
    
    cp -r * "$INSTALL_DIR/"
    cd -
    rm -rf "$TEMP_DIR"
fi

# Права
chmod +x "$INSTALL_DIR/bin/vps-watchdog"
chmod 600 "$INSTALL_DIR/config/"* 2>/dev/null || true

# Устанавливаем CLI команду
ln -sf "$INSTALL_DIR/bin/vps-watchdog" /usr/local/bin/vps-watchdog

# Создаём systemd service
cat > /etc/systemd/system/vps-watchdog.service <<EOF
[Unit]
Description=VPS Watchdog v3.0 - Multi-VM Monitor
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStartPre=/usr/bin/docker-compose -f $INSTALL_DIR/docker-compose.yml down
ExecStart=/usr/bin/docker-compose -f $INSTALL_DIR/docker-compose.yml up --build
ExecStop=/usr/bin/docker-compose -f $INSTALL_DIR/docker-compose.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
systemctl daemon-reload

echo
echo -e "${GREEN}${BOLD}✅ VPS Watchdog v${VERSION} установлен!${NC}"
echo
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo
echo -e "${BOLD}📋 ЧТО ДАЛЬШЕ:${NC}"
echo
echo "1️⃣  Запусти меню для настройки:"
echo -e "   ${GREEN}sudo vps-watchdog${NC}"
echo
echo "2️⃣  Добавь профиль VM (пункт 2 в меню)"
echo "   • Используй OAuth для автоматического добавления"
echo "   • Скрипт сам найдёт все твои VM"
echo
echo "3️⃣  Настрой Telegram бота (пункт 6)"
echo "   • Создай бота через @BotFather"
echo "   • Укажи токен и chat_id"
echo
echo "4️⃣  Запусти сервис:"
echo -e "   ${GREEN}sudo systemctl start vps-watchdog${NC}"
echo
echo "5️⃣  Проверь логи:"
echo -e "   ${GREEN}sudo docker logs -f vps-watchdog${NC}"
echo
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo
echo -e "${BOLD}📚 Документация:${NC} $REPO_URL"
echo -e "${BOLD}🐛 Баги:${NC} $REPO_URL/issues"
echo
