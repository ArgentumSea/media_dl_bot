#!/bin/bash
set -e

PROJECT_DIR="/opt/media_dl_bot"

cd "$PROJECT_DIR"
git pull
source venv/bin/activate
pip install -r requirements.txt

echo "Running migrations..."
PYTHONPATH="$PROJECT_DIR" python3 -c "import asyncio; from bot.database import migrate; asyncio.run(migrate())"

echo "Restarting bot..."
systemctl restart media_dl_bot
echo "Update complete."
