services:
  vps-watchdog:
    build: ./app
    container_name: vps-watchdog
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./profiles:/app/profiles:ro
