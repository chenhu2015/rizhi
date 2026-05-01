# rizhi — Setup Guide

Complete step-by-step instructions to go from zero to a running instance. Estimated time: 1–2 hours.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Claude Code Pro/Max subscription | The scanning agent — no separate API key needed |
| OCI free-tier VM | Ubuntu 22.04 LTS, at least 1 OCPU + 1 GB RAM |
| GitHub account | For the rizhi repo and the papers-vault repo |
| Domain name | Required for HTTPS and phone push notifications |
| Python 3.10+ on local machine | For local development and testing |

---

## 1. Local development setup

### Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/rizhi.git
cd rizhi
pip install -e ".[dev]"
```

### Verify the scanner works

```bash
pytest tests/ -v              # 5 tests should pass
python -m scanner.fetch       # hits arxiv, prints JSON papers to stdout
```

The fetch will print a JSON array of recent papers. If you see papers, the scanner is working.

### Windows note

Developed on Windows, deployed on Linux — this works fine. Two things are handled automatically:
- `.gitattributes` ensures shell scripts keep Unix line endings on Linux
- `pathlib` is used everywhere for cross-platform paths

---

## 2. OCI VM setup

### VM specs (free tier)

OCI always-free tier includes an ARM-based VM (Ampere A1) with 4 OCPUs and 24 GB RAM — far more than needed. Ubuntu 22.04 LTS is the recommended OS.

### SSH access

Configure an SSH alias on your local machine (`~/.ssh/config`):

```
Host OCI-Desktop
  HostName <your-vm-public-ip>
  IdentityFile ~/.ssh/oci-ssh-key.key
  User ubuntu
```

Test: `ssh OCI-Desktop "echo connected"`

### OCI Security List (cloud-level firewall)

OCI has two firewall layers. The OS-level one (ufw) is handled by `setup.sh`. The cloud-level one must be opened manually:

1. OCI Console → **Networking** → **Virtual Cloud Networks** → your VCN
2. **Security Lists** → **Default Security List** → **Add Ingress Rules**
3. Add two rules:

| Source CIDR | Protocol | Port | Purpose |
|-------------|----------|------|---------|
| 0.0.0.0/0 | TCP | 80 | HTTP (certbot verification + redirect to HTTPS) |
| 0.0.0.0/0 | TCP | 443 | HTTPS (PWA + API) |

SSH (port 22) should already be open. Keep it restricted to your home IP for better security.

---

## 3. Domain name

A domain is required for HTTPS, which is required for Web Push notifications and PWA install.

### Getting a domain (Cloudflare Registrar)

1. Go to **cloudflare.com** → create a free account
2. **Domain Registration** → **Register Domains** → search for your name
3. Recommended: `.com` (~$9/yr), `.dev` (~$12/yr), `.me` (~$10/yr)
4. Purchase — takes 2 minutes

### DNS records

In Cloudflare DNS, add two A records:

| Type | Name | IPv4 | Proxy status |
|------|------|------|--------------|
| A | `rizhi` | your OCI public IP | DNS only (grey cloud) |
| A | `@` | your OCI public IP | DNS only (grey cloud) |

**Important:** Keep proxy status as **grey cloud (DNS only)**. If you enable Cloudflare proxy (orange cloud), nginx rate limiting breaks because all requests appear to come from Cloudflare's IPs. See the Security section below for how to enable it properly if needed.

Verify DNS propagated (takes ~5 minutes):
```bash
nslookup rizhi.yourdomain.com   # should return your OCI IP
```

---

## 4. Deploy to OCI

### Clone the repo on OCI

```bash
ssh OCI-Desktop "mkdir -p ~/claude-project && git clone https://github.com/YOUR_USERNAME/rizhi.git ~/claude-project/rizhi"
```

### Install Python dependencies

```bash
ssh OCI-Desktop "python3 -m venv ~/.venv && ~/.venv/bin/pip install -q -e ~/claude-project/rizhi"
```

### Run setup.sh

This installs nginx, certbot (via snap), configures systemd, opens OS firewall ports, and sets up the daily cron job:

```bash
ssh OCI-Desktop "bash ~/claude-project/rizhi/deploy/setup.sh"
```

If setup.sh fails mid-way, re-run it — it is safe to run multiple times.

### Get the HTTPS certificate

```bash
ssh OCI-Desktop "sudo certbot --nginx -d rizhi.yourdomain.com --non-interactive --agree-tos -m your@email.com"
```

**Note:** Install certbot via snap, not apt — the apt version has Python 3.12 compatibility issues:
```bash
# If certbot --nginx fails with a Python error, reinstall via snap:
sudo apt-get remove -y certbot python3-certbot-nginx
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

---

## 5. Environment configuration

### Generate credentials on OCI

```bash
ssh OCI-Desktop "cd ~/claude-project/rizhi && ~/.venv/bin/python -c \"
import secrets, base64
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
from py_vapid import Vapid

token = secrets.token_urlsafe(32)
v = Vapid()
v.generate_keys()
priv = base64.urlsafe_b64encode(v._private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())).decode().rstrip('=')
pub  = base64.urlsafe_b64encode(v._public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)).decode().rstrip('=')

print('Bearer token:', token)
print('VAPID public:', pub)

with open('.env', 'w') as f:
    f.write(f'RIZHI_BEARER_TOKEN={token}\n')
    f.write(f'VAPID_PRIVATE_KEY={priv}\n')
    f.write(f'VAPID_PUBLIC_KEY={pub}\n')
    f.write('VAPID_CLAIMS_EMAIL=your@email.com\n')
    f.write('CLAUDE_BIN=/home/ubuntu/.cache/claude/staging/REPLACE_WITH_ACTUAL_PATH/claude\n')
print('.env written.')
\""
```

**Save the bearer token** — you will enter it once in the PWA on first launch.

### Find the Claude binary path

```bash
ssh OCI-Desktop "find ~/.cache/claude -name 'claude' -type f 2>/dev/null"
```

Update `CLAUDE_BIN` in `.env` with the full path shown.

### Restart the server to load .env

```bash
ssh OCI-Desktop "sudo systemctl restart rizhi"
```

---

## 6. papers-vault (Obsidian knowledge base)

The scanner writes Obsidian-formatted markdown notes to a separate git repo. This repo is your permanent knowledge base — it lives on OCI and syncs to your local machine via GitHub.

### Create the GitHub repo

1. Go to github.com → New repository → name it `papers-vault`
2. Keep it **private** (it will contain your personal research notes)
3. Do not initialise with any files

### Set up SSH deploy key on OCI

The OCI VM needs to push to GitHub. A deploy key is safer than using your personal SSH key:

```bash
# Generate a key on OCI
ssh OCI-Desktop "ssh-keygen -t ed25519 -f ~/.ssh/papers-vault-deploy -N '' -C 'rizhi-papers-vault'"

# Show the public key — copy this
ssh OCI-Desktop "cat ~/.ssh/papers-vault-deploy.pub"
```

Add the public key to GitHub:
- Go to `github.com/YOUR_USERNAME/papers-vault` → **Settings** → **Deploy keys** → **Add deploy key**
- Title: `OCI rizhi`
- Key: paste the public key
- Check **Allow write access**

Configure SSH on OCI to use this key for GitHub:

```bash
ssh OCI-Desktop "cat >> ~/.ssh/config << 'EOF'

Host github-papers-vault
  HostName github.com
  User git
  IdentityFile ~/.ssh/papers-vault-deploy
EOF"
```

### Clone and initialise the vault

```bash
ssh OCI-Desktop "
git clone git@github-papers-vault:YOUR_USERNAME/papers-vault.git ~/claude-project/papers-vault
mkdir -p ~/claude-project/papers-vault/papers ~/claude-project/papers-vault/digests
echo '# papers-vault' > ~/claude-project/papers-vault/README.md
cd ~/claude-project/papers-vault && git add . && git commit -m 'init' && git push origin main"
```

### Local Obsidian setup

1. Clone `papers-vault` to your local machine:
   ```bash
   git clone https://github.com/YOUR_USERNAME/papers-vault.git ~/claude-project/papers-vault
   ```
2. Open Obsidian → **Open folder as vault** → select `~/claude-project/papers-vault`
3. Install the **Obsidian Git** plugin (community plugins)
4. Configure Obsidian Git:
   - Pull on vault open: **yes**
   - Auto commit + push interval: 10 minutes (or on close)

---

## 7. Verify the full stack

### Check server is running

```bash
curl -s -o /dev/null -w "%{http_code}" https://rizhi.yourdomain.com
# Should return: 200
```

### Check authenticated API

```bash
curl -s \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN" \
  https://rizhi.yourdomain.com/api/results/latest
# Should return: []  (empty — no papers yet)
```

### Run a manual scan

Trigger Claude Code manually to test the full pipeline:

```bash
ssh OCI-Desktop "
CLAUDE=/home/ubuntu/.cache/claude/staging/REPLACE/claude
cd ~/claude-project/rizhi
\$CLAUDE --print < agent/CLAUDE.md
"
```

This will:
1. Fetch papers from arxiv
2. Claude scores each one against your interest profile
3. Write `results/YYYY-MM-DD.json`
4. Write Obsidian vault notes to `~/claude-project/papers-vault/`
5. Git commit and push the vault
6. Trigger push notification to your phone (if PWA is set up)

### Watch scan logs

```bash
ssh OCI-Desktop "tail -f /var/log/rizhi-scan.log"
```

---

## 8. PWA on your phone

1. Open **Safari** on iPhone (or Chrome on Android)
2. Navigate to `https://rizhi.yourdomain.com`
3. Enter your bearer token when prompted (stored, never asked again)
4. Tap **Enable** when the notification permission banner appears
5. iOS: tap the Share button → **Add to Home Screen**
   Android: tap the browser menu → **Add to Home Screen** or **Install app**

The app icon appears on your home screen. Push notifications will arrive each morning after the 06:00 UTC scan.

---

## 9. Keeping it updated

### Pull latest code on OCI after local changes

```bash
# Local: commit and push
git add . && git commit -m "your changes" && git push origin main

# OCI: pull and restart
ssh OCI-Desktop "cd ~/claude-project/rizhi && git pull && sudo systemctl restart rizhi"
```

### Update Claude binary path after Claude Code upgrades

```bash
ssh OCI-Desktop "find ~/.cache/claude -name 'claude' -type f"
# Update CLAUDE_BIN in .env and in crontab
ssh OCI-Desktop "crontab -e"
```

---

## Security

### Current setup

| Layer | Protection |
|-------|-----------|
| OCI Security List | Only ports 22, 80, 443 open |
| OS firewall (ufw) | Same rules, second layer |
| nginx rate limiting | 10 requests/minute per IP on API endpoints |
| Bearer token auth | All API endpoints require `Authorization: Bearer TOKEN` |
| `/internal/notify` | Blocked by nginx from outside; accepts localhost only |
| HTTPS | Let's Encrypt certificate, auto-renews via certbot |
| SSH | Key-only auth, no password login |

### Cloudflare proxy (optional upgrade)

Switching Cloudflare DNS from grey to orange cloud adds DDoS protection and hides your real IP. It requires two nginx changes:

1. Add Cloudflare IP ranges to nginx so real client IPs are restored (needed for rate limiting):
```nginx
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 131.0.72.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;
real_ip_header X-Forwarded-For;
```

2. In Cloudflare dashboard: **SSL/TLS** → set mode to **Full (Strict)**

For a personal single-user app this upgrade is optional — the current setup handles all realistic threats.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `scanner.fetch` returns `[]` | Papers already marked seen — delete `storage/seen_papers.db` and retry |
| Certbot fails with Python error | Reinstall via snap: `sudo snap install --classic certbot` |
| nginx config fails with `options-ssl-nginx.conf not found` | Run certbot first to generate the cert, then install the full nginx config |
| Push notifications not arriving | Check VAPID keys in `.env`; check browser notification permission; ensure PWA is installed via Safari (iOS) |
| `systemctl status rizhi` shows failed | Check logs: `journalctl -u rizhi -n 50` |
| Claude binary not found by cron | Run `find ~/.cache/claude -name 'claude' -type f` and update `CLAUDE_BIN` in `.env` and crontab |
| OCI Security List ports not open | OCI Console → Networking → VCN → Security Lists → Default → Add ingress rules for 80 and 443 |
