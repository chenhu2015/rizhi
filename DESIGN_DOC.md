# rizhi (日知) — Design Document

**Version:** 0.5
**Last updated:** 2026-04-29

---

## Overview

A 24/7 service running on an OCI virtual machine that periodically scans arxiv and other academic sources, filters papers based on user interests using Claude Code, and delivers push notifications to the user's phone via a personal PWA (Progressive Web App). The user can view paper summaries, adjust interest settings, and trigger manual scans — all from the phone.

---

## Core Flow

```
OCI VM
├── Claude Code (cron, once per day)
│     fetches papers from arxiv / Semantic Scholar
│     scores relevance + generates summaries
│     writes results/latest.json          → FastAPI picks up → push notification
│     writes papers vault markdown files  → git commit + push → GitHub
│
├── FastAPI server (systemd, always running)
│     watches results/latest.json for changes
│     serves the PWA (static files)
│     manages Web Push subscriptions
│     sends Web Push notification when new results arrive
│
└── SQLite  ←  deduplication (seen paper IDs)

          ↓  HTTPS / Web Push                    ↓  git pull

User's Phone / Browser                   Local Computer (Obsidian)
└── PWA (installed to home screen)       └── papers vault (git repo)
      receives push notification               read papers, add own notes
      opens → shows paper digest              organized by date / topic / tag
      works on iOS and Android                synced from GitHub
```

---

## Project Structure

Two separate git repositories:

**rizhi** (this repo — service code):
```
rizhi/
├── scanner/
│   ├── arxiv_client.py         # arxiv API queries
│   ├── web_client.py           # Semantic Scholar / RSS feeds
│   ├── scorer.py               # relevance scoring via Claude Code agent
│   └── interest_profile.yaml   # user interest configuration (edit to change topics)
├── agent/
│   └── CLAUDE.md               # instructions for the OCI Claude Code session
├── server/
│   ├── main.py                 # FastAPI app: serves PWA + Web Push endpoints
│   ├── push.py                 # Web Push logic (pywebpush + VAPID keys)
│   └── static/                 # PWA: index.html, app.js, sw.js, manifest.json
├── results/
│   ├── 2026-04-29.json         # one file per day
│   └── latest.json             # symlink to today's file; FastAPI watches this
├── storage/
│   └── seen_papers.db          # SQLite, prevents duplicate notifications
├── deploy/
│   ├── rizhi.service           # systemd unit for FastAPI server
│   ├── nginx.conf              # reverse proxy + rate limiting config
│   └── setup.sh                # one-shot OCI setup script
├── config.yaml                 # scan interval, max papers, score threshold
├── requirements.txt
├── README.md
└── DESIGN_DOC.md
```

**papers-vault** (separate repo — Obsidian knowledge base, synced to GitHub):
```
papers-vault/
├── papers/
│   └── 2026/
│       └── MM/
│           └── YYYY-MM-DD-paper-slug.md   # one file per paper
├── digests/
│   └── YYYY-MM-DD.md                      # daily index note
└── README.md
```

---

## User Journey

Two endpoints, two different modes of use. They are complementary, not redundant.

### Phone — quick triage

```
6:00 AM  Claude Code scan finishes on OCI VM
         → push notification arrives on phone:
           "3 new papers: GRPO reward shaping, VLM tool use agent, ..."

Morning  User taps notification → PWA opens
         Skims titles and one-paragraph summaries
         Marks 2 as "worth reading" (or just remembers)
         Taps arxiv link on one to skim the abstract in browser

Done in 3 minutes. No deep reading on phone.
```

### Local computer — deep reading

```
Later    User opens Obsidian
         Obsidian Git plugin auto-pulls from GitHub on open
         New paper notes appear in papers/2026/04/

         Opens digests/2026-04-29.md → index of today's papers
         Clicks into a paper note → reads Claude's summary + key contributions
         Adds own thoughts in "## My Thoughts"
         Updates status: unread → done

         Obsidian Git auto-pushes annotations back to GitHub
```

### What each endpoint provides

| | Phone (PWA) | Local (Obsidian) |
|--|--|--|
| Push notification | Yes | No — Obsidian Git auto-pulls on open |
| Quick skim | Yes | No |
| Deep reading | No | Yes |
| Add own notes | No | Yes |
| Browse history | Last 7 days | All time |
| Adjust scan settings | Yes | No |
| Trigger manual scan | Yes | No |

---

## Component Design

### 1. Data Sources

| Source | API | Coverage | Auth |
|--------|-----|----------|------|
| arxiv | `export.arxiv.org/api/query` | CS / AI / physics / math / biology | Free, no key |
| Semantic Scholar | `api.semanticscholar.org` | All disciplines, includes citation counts | Free, no key |
| RSS feeds | Per-journal RSS | Extensible | Free |

### 2. Interest Profile (`interest_profile.yaml`)

```yaml
topics:
  - reinforcement learning
  - agentic RL
  - RL training
  - multimodal models
  - vision language models

keywords:
  - RLHF
  - RLAIF
  - PPO
  - reward model
  - agentic
  - tool use
  - multimodal
  - vision-language
  - VLM
  - LLM agent

authors: []  # add specific researchers to follow later

min_score: 0.7        # Claude relevance score threshold (0-1)
max_papers_per_run: 5 # max papers pushed per daily run
```

### 3. Scorer (Claude Code Agent)

- Claude Code runs as a cron job on the OCI VM using the user's Pro/Max subscription
- No separate Anthropic API key required
- The agent reads `agent/CLAUDE.md` for instructions each run
- Fetches paper abstracts → judges relevance → generates English summaries
- Writes results above `min_score` to `results/latest.json`
- Session exits after each run (not a persistent daemon)

**Future: Ollama Integration**
- Run Ollama on the OCI VM for initial keyword filtering (cheaper)
- Claude Code handles only final relevance judgment and summary generation
- Division of labor: Ollama pre-filters → Claude Code scores + summarizes

### 4. FastAPI Server

- Runs as a systemd service (always on)
- All endpoints require `Authorization: Bearer <TOKEN>`
- Endpoint groups:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/push/subscribe` | POST | Store Web Push subscription from PWA |
| `/api/push/unsubscribe` | POST | Remove subscription |
| `/api/results/latest` | GET | Return today's results |
| `/api/results/history` | GET | Return last 7 days of results (for PWA history view) |
| `/api/config` | GET / POST | Read or update `interest_profile.yaml` |
| `/api/config/keywords` | POST | Add / remove individual keywords |
| `/api/scan` | POST | Trigger an immediate Claude Code scan |
| `/api/scan/status` | GET | Return current scan status (idle / running / done) — PWA polls this after triggering a scan |

- On new results: sends Web Push to all stored subscriptions via pywebpush
- Results are stored as `results/YYYY-MM-DD.json` per day; `latest.json` is a symlink to today's file

### 5. PWA (Progressive Web App)

A PWA is a regular website that the browser lets you install like a native app — it gets a home screen icon, runs full-screen with no address bar, works offline, and can receive push notifications. No app store, no Xcode, no Android Studio. Built with plain HTML / JavaScript / CSS plus two extra files:

- **`manifest.json`** — declares the app name, icon, and theme color so the browser knows how to install it
- **`sw.js`** (service worker) — a background script that receives push events and caches content for offline use

**Compatibility:**
- Android: any browser (Chrome, Firefox, Samsung Internet)
- iOS: Safari only for install and push notifications (Chrome on iOS cannot)

**What the PWA provides:**

| Screen | Function |
|--------|---------|
| Today | Today's papers — title, score, one-paragraph summary, arxiv link |
| History | Papers from the last 7 days, grouped by date — so a missed day is never lost |
| Settings | Edit topics, keywords, authors, min_score, max papers per run |
| Scan | Trigger an immediate scan; polls `/api/scan/status` every 5 seconds and shows live status until done |

**Interaction flow — phone to server:**
- PWA sends authenticated API requests to FastAPI on the OCI VM
- Example: user adds "GRPO" as a keyword → `POST /api/config/keywords` → FastAPI updates `interest_profile.yaml` → next Claude Code run picks it up
- Example: user taps "Scan Now" → `POST /api/scan` → PWA polls `/api/scan/status` → shows "Scanning… done. 2 new papers found."

**First-launch setup:**
1. Visit `https://rizhi.yourdomain.com` in Safari (iOS) or Chrome (Android)
2. Enter bearer token (one-time)
3. Allow notifications when prompted — browser registers a Web Push subscription
4. PWA posts subscription to `/api/push/subscribe`
5. Tap "Add to Home Screen" → installed as an app icon

### 6. Notification Flow

```
Claude Code writes results/latest.json
    ↓
FastAPI detects new file (cron triggers a POST to /internal/notify, or file watcher)
    ↓
FastAPI sends Web Push to each stored subscription (pywebpush + VAPID)
    ↓
Phone receives push notification (regardless of whether PWA is open)
    ↓
User taps → PWA opens → paper digest displayed
```

Web Push notifications arrive independently of any Claude Code session state — no Remote Control connection required.

---

## Knowledge Base (Obsidian Vault)

### Concept

Every paper that passes the score threshold gets written as an Obsidian-compatible markdown file into a dedicated **papers vault git repo** on the OCI VM. After each scan, Claude Code commits and pushes to GitHub. The user pulls locally and opens the vault in Obsidian to read, annotate, and connect ideas.

This separates two concerns:
- **rizhi repo** — service code (scanner, server, deploy config)
- **papers vault repo** — living knowledge base (paper notes, personal annotations)

### Vault Structure

```
papers-vault/
├── papers/
│   ├── 2026/
│   │   ├── 04/
│   │   │   ├── 2026-04-29-grpo-reward-shaping.md
│   │   │   └── 2026-04-29-vlm-tool-use-agent.md
│   │   └── ...
├── digests/
│   │   ├── 2026-04-29.md   ← daily index note linking all papers found that day
│   │   └── ...
└── README.md
```

### Paper Note Format

Each paper gets one markdown file. Claude Code writes the top section; the user fills in "My Thoughts".

```markdown
---
title: "Reward Shaping via GRPO for Agentic Tasks"
authors: ["Author A", "Author B"]
date: 2026-04-29
arxiv_id: "2404.12345"
url: "https://arxiv.org/abs/2404.12345"
score: 0.91
topics: [RL, agentic-RL, reward-model]
status: unread
---

# Reward Shaping via GRPO for Agentic Tasks

## Summary
<!-- Written by Claude Code -->
...

## Key Contributions
<!-- Written by Claude Code -->
- ...

## Relevance
<!-- Written by Claude Code — why this matches current interests -->
...

## My Thoughts
<!-- User fills in manually -->

```

**Obsidian features used:**
- **YAML frontmatter** — queryable via Dataview plugin (e.g. list all unread papers with score > 0.85)
- **`#tags`** in the body for topic browsing
- **`[[wikilinks]]`** — Claude Code links related papers by title when detected
- **`status: unread → reading → done`** — user updates manually to track progress
- **Daily digest note** in `digests/` links all papers found that day

### Git Workflow

```
OCI VM (after each scan)
    git -C ~/claude-project/papers-vault pull --rebase origin main   ← pull first to avoid conflict
    git -C ~/claude-project/papers-vault add papers/ digests/
    git -C ~/claude-project/papers-vault commit -m "digest: 2026-04-29 (3 papers)"
    git -C ~/claude-project/papers-vault push origin main

Local computer (automatic via Obsidian Git plugin)
    on vault open  → git pull
    on vault close → git add + commit + push (annotations only)
```

**Why conflicts are safe to avoid:**
- OCI VM only ever adds new files (`papers/YYYY/MM/new-paper.md`, `digests/YYYY-MM-DD.md`)
- You only ever modify existing files (adding "My Thoughts", updating `status`)
- These never touch the same lines, so even if a pull-rebase is needed, it resolves cleanly

The `--rebase` on the OCI side means: if you pushed annotations since the last scan, the new paper files get layered on top cleanly without a merge commit.

The [Obsidian Git plugin](https://github.com/denolehov/obsidian-git) handles the local side automatically — configure it to pull on open and push on close.

### What Claude Code Writes vs. What You Write

| Section | Author |
|---------|--------|
| YAML frontmatter | Claude Code |
| Summary | Claude Code |
| Key Contributions | Claude Code |
| Relevance (why it matches interests) | Claude Code |
| Wikilinks to related papers | Claude Code |
| My Thoughts | You |
| status field updates | You |

---

## Security Design

### Threat Model

This is a personal single-user app. The realistic threats are automated bot scanning and SSH brute force, not targeted attacks. No sensitive user data is stored.

### Defense Layers

**1. OCI Security Group (network perimeter)**

| Port | Source | Reason |
|------|--------|--------|
| 443 (HTTPS) | 0.0.0.0/0 | PWA and Web Push |
| 80 (HTTP) | 0.0.0.0/0 | Redirect to HTTPS only |
| 22 (SSH) | owner IP only | Never open SSH to the world |

All other ports closed at OCI level before traffic reaches the VM.

**2. SSH hardening**
```
PasswordAuthentication no   # key-only auth
PermitRootLogin no
```

**3. nginx as reverse proxy**
- Terminates TLS (Let's Encrypt)
- Strips malformed requests before FastAPI sees them
- Rate limiting: 10 requests/minute per IP on API endpoints
- FastAPI binds to `127.0.0.1:8000` only — never directly exposed

**4. Application auth**
- All FastAPI endpoints require `Authorization: Bearer <TOKEN>`
- Token stored in PWA localStorage after first setup
- 401 for unauthenticated requests — no login page to brute-force

**5. Fail2ban**
- Auto-bans IPs with repeated SSH failures or excessive 4xx responses from nginx

**6. Unattended upgrades**
- Automatic security patches applied to Ubuntu packages

### What Is Not Exposed

- Claude Code — runs as a cron job, never listens on a port
- SQLite database — local file only
- `results/` folder — read by FastAPI internally, not served as raw files

---

## OCI Deployment

| Component | How it runs |
|-----------|-------------|
| Claude Code scanner | cron job, once per day |
| FastAPI server | systemd service (`rizhi.service`) |
| nginx | systemd service |
| SQLite | local file |
| Let's Encrypt cert | certbot auto-renew (cron) |

---

## Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Interest areas | RL/agentic RL training, multimodal models ✓ |
| 2 | Scan frequency | Once per day ✓ |
| 3 | Notification method | Web Push via PWA ✓ |
| 4 | Anthropic API key | Not needed — using Claude Code Pro/Max ✓ |
| 5 | OCI VM OS | Ubuntu 22.04 LTS ✓ |
| 6 | Domain name | To be configured (required for HTTPS/Web Push) |

---

## Pending

- OCI VM credentials (user to provide)
- Domain name for HTTPS
- Specific author watchlist
- VAPID key generation (one-time setup)
- Create `papers-vault` GitHub repo and configure SSH deploy key on OCI VM
- Decide on Obsidian vault location on local machine
