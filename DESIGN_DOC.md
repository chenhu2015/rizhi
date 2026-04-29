# rizhi (日知) — Design Document

**Version:** 0.1 (draft)
**Last updated:** 2026-04-29

---

## Overview

A 24/7 service running on an OCI virtual machine that periodically scans arxiv and other academic sources, filters papers based on user interests, and delivers push notifications to the user's phone via Claude Code Remote Control. The user can view summaries and interact with Claude directly from mobile.

---

## Core Flow

```
OCI VM (Claude Code agent running continuously, using Pro/Max subscription)
  ↓ once per day (cron)
Scanner fetches new papers (arxiv / Semantic Scholar / RSS)
  ↓
[Future] Ollama pre-filter (local model, cheaper)
  ↓
Claude Code agent scores relevance + generates English summaries
  ↓
High-score papers → push notification to phone (Claude Code push notification)
  ↓
Tap notification → claude.ai mobile connects to OCI remote session
  ↓
View paper summaries / interact with Claude
```

---

## Project Structure

```
paper-scout/
├── scanner/
│   ├── arxiv_client.py         # arxiv API queries
│   ├── web_client.py           # Semantic Scholar / RSS feeds
│   ├── scorer.py               # relevance scoring via Claude Code agent
│   └── interest_profile.yaml   # user interest configuration
├── agent/
│   └── CLAUDE.md               # instructions for the OCI Claude Code session
├── storage/
│   └── seen_papers.db          # SQLite, prevents duplicate notifications
├── deploy/
│   ├── paper-scout.service     # systemd unit file
│   └── setup.sh                # one-shot OCI setup script
├── config.yaml                 # scan schedule, sources, score threshold
├── requirements.txt
└── DESIGN_DOC.md               # this file
```

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

### 3. Scorer

- Claude Code runs as the agent on the OCI VM using the user's Pro/Max subscription
- No separate Anthropic API key required
- Claude Code agent is responsible for: fetching papers → reading abstracts → judging relevance → generating summaries
- Only papers above `min_score` enter the notification queue

**Future: Ollama Integration**
- Run Ollama on the OCI VM (local open-source models)
- Handle low-value subtasks such as initial keyword filtering (cheaper)
- Claude Code handles only final relevance judgment and summary generation (high-value tasks)
- Division of labor: Ollama pre-filters → Claude Code scores + summarizes

### 4. Notification and Mobile Viewing

- Claude Code runs as a persistent agent on the OCI VM
- When high-score papers are found, the agent compiles a digest and triggers a push notification
- Phone receives notification via the claude.ai app
- Tapping the notification connects to the OCI remote session — user can browse the list and ask follow-up questions

### 5. OCI Deployment

- systemd service keeps the Claude Code agent alive
- Scanner runs once per day via cron
- SQLite tracks already-seen paper IDs to prevent duplicate notifications

---

## Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Interest areas | RL/agentic RL training, multimodal models ✓ |
| 2 | Scan frequency | Once per day ✓ |
| 3 | Project folder name | `paper-scout` ✓ |
| 4 | Anthropic API key | Not needed — using Claude Code Pro/Max as agent ✓ |
| 5 | OCI VM OS | Ubuntu 22.04 LTS ✓ |

---

## Pending

- OCI VM credentials (user to provide later)
- Specific author watchlist
- Claude Code Remote Control setup on OCI (needs verification once VM is connected)
