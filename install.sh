#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/vps-watchdog"
BIN_PATH="/usr/local/bin/vps-watchdog"
SERVICE_PATH="/etc/systemd/system/vps-watchdog.service"

# ВАЖНО: это твой репозиторий
REPO_URL="https://github.com/Mastachok/ya-vps-autostart.git"
REPO_BRANCH="main"

need_root() { [[ "${EUID}" -eq 0 ]] || { echo "Запусти: sudo bash install.sh"; exit 1; }; }
have_cmd() { command -v "$1" >/dev/null 2>&1; }

install_deps() {
  apt-get update -y
  apt-get install -y ca-certificates curl git jq whiptail
}

check_docker() {
  if ! have_cmd docker; then
    echo "Docker не найден. Установи Docker + Compose v2."
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "docker compose (v2) не найден. Установи Docker Compose v2."
    exit 1
  fi
}

clone_or_update_repo() {
  if [[ -d "$APP_DIR/.git" ]]; then
    echo "Repo уже есть, обновляю..."
    git -C "$APP_DIR" fetch --all -q
    git -C "$APP_DIR" checkout -q "$REPO_BRANCH"
    git -C "$APP_DIR" pull -q
  else
    echo "Клонирую $REPO_URL -> $APP_DIR"
    rm -rf "$APP_DIR"
    git clone -q --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
  fi
}

install_menu_binary() {
  install -m 0755 "$APP_DIR/bin/vps-watchdog" "$BIN_PATH"
}

install_systemd() {
  install -m 0644 "$APP_DIR/templates/systemd.service.tpl" "$SERVICE_PATH"
  systemctl daemon-reload
  systemctl enable vps-watchdog.service
}

first_bootstrap() {
  mkdir -p "$APP_DIR/profiles"
  if [[ ! -f "$APP_DIR/ACTIVE_PROFILE" ]]; then
    echo "default" > "$APP_DIR/ACTIVE_PROFILE"
  fi
  # если профиля default нет — создадим заглушку (потом в меню сделаешь нормальный)
  if [[ ! -f "$APP_DIR/profiles/default.env" ]]; then
    cat > "$APP_DIR/profiles/default.env" <<'EOF'
PROFILE_NAME=default
VM_HOST=1.1.1.1
INSTANCE_ID=replace-me
CHECK_INTERVAL=60
PING_ATTEMPTS=5
PING_TIMEOUT=5
SA_KEY_FILE=/app/profiles/default.sa-key.json
EOF
    touch "$APP_DIR/profiles/default.sa-key.json"
    chmod 600 "$APP_DIR/profiles/default.sa-key.json" || true
  fi

  # активный .env = копия из active profile
  PROFILE="$(cat "$APP_DIR/ACTIVE_PROFILE")"
  cp -f "$APP_DIR/profiles/${PROFILE}.env" "$APP_DIR/.env"
}

start_service() {
  systemctl start vps-watchdog.service
}

main() {
  need_root
  install_deps
  check_docker
  clone_or_update_repo
  first_bootstrap
  install_menu_binary
  install_systemd
  start_service

  echo "✅ Установлено."
  echo "Меню: sudo vps-watchdog"
  echo "Статус: systemctl status vps-watchdog --no-pager"
}

main "$@"
