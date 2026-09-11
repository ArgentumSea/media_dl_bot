#!/bin/bash
set -e

PROJECT_DIR="/opt/media_dl_bot"
REPO_URL="https://github.com/ArgentumSea/media_dl_bot.git"
DB_NAME="media_dl_bot"
DB_USER="bot_user"
DB_PASS="bot_password"

echo "Installing dependencies..."
apt-get update
apt-get install -y python3-pip python3-venv python3-dev build-essential postgresql postgresql-contrib git ffmpeg

echo "Cloning repository..."
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR"
    git pull
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Setting up PostgreSQL..."
su - postgres -c "psql -c 'CREATE DATABASE $DB_NAME;'" 2>/dev/null || true
su - postgres -c "psql -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';\"" 2>/dev/null || true
su - postgres -c "psql -c 'GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;'" 2>/dev/null || true
su - postgres -c "psql -d $DB_NAME -c 'GRANT ALL ON SCHEMA public TO $DB_USER;'" 2>/dev/null || true

echo "Creating .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "============================================"
    echo "EDIT .env FILE BEFORE STARTING THE BOT"
    echo "============================================"
fi

echo "Setting up systemd service..."
cp media_dl_bot.service /etc/systemd/system/media_dl_bot.service
systemctl daemon-reload

echo "Setup complete."
echo "1. Edit $PROJECT_DIR/.env"
echo "2. Run: systemctl enable --now media_dl_bot"
