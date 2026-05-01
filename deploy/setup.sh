#!/bin/bash
# One-shot setup script for the OCI Ubuntu 22.04 VM.
# Run as the ubuntu user: bash ~/claude-project/rizhi/deploy/setup.sh
set -euo pipefail

RIZHI_DIR="$HOME/claude-project/rizhi"
VENV_DIR="$HOME/.venv"

echo "=== rizhi setup ==="

# --- system packages ---
sudo apt-get update -qq
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev \
    nginx certbot python3-certbot-nginx git curl

# --- Python venv ---
python3.12 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$RIZHI_DIR"

# --- .env file ---
if [ ! -f "$RIZHI_DIR/.env" ]; then
    cp "$RIZHI_DIR/.env.example" "$RIZHI_DIR/.env"
    echo ""
    echo "  Created .env from .env.example."
    echo "  Edit it now:  nano $RIZHI_DIR/.env"
    echo ""
fi

# --- papers-vault repo ---
if [ ! -d "$HOME/claude-project/papers-vault/.git" ]; then
    echo ""
    echo "  papers-vault not found at ~/claude-project/papers-vault."
    echo "  Clone it manually:"
    echo "    git clone git@github.com:YOU/papers-vault.git ~/claude-project/papers-vault"
    echo ""
fi

# --- systemd service ---
sudo cp "$RIZHI_DIR/deploy/rizhi.service" /etc/systemd/system/rizhi.service
sudo systemctl daemon-reload
sudo systemctl enable rizhi
sudo systemctl start rizhi
echo "  FastAPI server: started (systemd)"

# --- nginx ---
sudo cp "$RIZHI_DIR/deploy/nginx.conf" /etc/nginx/sites-available/rizhi
sudo ln -sf /etc/nginx/sites-available/rizhi /etc/nginx/sites-enabled/rizhi
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
echo "  nginx: configured"

# --- cron (daily scan at 06:00) ---
CRON_JOB="0 6 * * * cd $RIZHI_DIR && $HOME/.cache/claude/current/claude --print < agent/CLAUDE.md >> /var/log/rizhi-scan.log 2>&1"
( crontab -l 2>/dev/null | grep -v "rizhi-scan"; echo "$CRON_JOB" ) | crontab -
echo "  Cron: daily scan at 06:00"

# --- log file ---
sudo touch /var/log/rizhi-scan.log
sudo chown ubuntu:ubuntu /var/log/rizhi-scan.log

echo ""
echo "=== setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in .env:           nano $RIZHI_DIR/.env"
echo "  2. Generate VAPID keys:    $VENV_DIR/bin/python -m server.push --generate-keys"
echo "  3. Set up HTTPS:           sudo certbot --nginx -d your-domain.com"
echo "  4. Clone papers-vault:     git clone git@github.com:YOU/papers-vault.git ~/claude-project/papers-vault"
echo "  5. Check server status:    sudo systemctl status rizhi"
echo "  6. Watch scan logs:        tail -f /var/log/rizhi-scan.log"
