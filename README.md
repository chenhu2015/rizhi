# rizhi (日知)

> 日知其所亡 — Know daily what you did not know before. *(Analects of Confucius)*

A self-hosted daily research paper digest. Runs on an OCI free-tier VM, scans arxiv and Semantic Scholar every morning, scores papers using Claude Code, and delivers a push notification to your phone. Read the digest in a PWA; annotate papers in Obsidian.

## What it does

- Fetches new papers daily from arxiv and Semantic Scholar (both free, no API key)
- Scores each paper for relevance using Claude Code (Pro/Max — no separate Anthropic API key needed)
- Pushes a notification to your phone when high-scoring papers arrive
- PWA on your phone: skim summaries, browse history, adjust keywords, trigger manual scans
- Saves Obsidian-formatted markdown notes to a git repo → sync to local machine → read and annotate

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Scoring agent | Claude Code (Pro/Max subscription) |
| Sources | arxiv API + Semantic Scholar API |
| Server | FastAPI + uvicorn |
| Notifications | Web Push (pywebpush + VAPID) |
| Frontend | PWA (plain HTML/JS, no framework) |
| Storage | SQLite |
| Reverse proxy | nginx |
| Deployment | Ubuntu 22.04 LTS, systemd, OCI free tier |
| Knowledge base | Obsidian vault synced via GitHub |

## Two endpoints

| | Phone (PWA) | Local computer (Obsidian) |
|--|-------------|--------------------------|
| Push notifications | Yes | No — auto-pulls on Obsidian open |
| Quick skim | Yes | No |
| Deep reading + notes | No | Yes |
| Adjust scan settings | Yes | No |

## Setup

See **[SETUP.md](SETUP.md)** for the full step-by-step guide — covers OCI VM, domain, HTTPS, PWA install, and Obsidian vault sync.

## Customise your interests

Edit `scanner/interest_profile.yaml` to change topics, keywords, score threshold, and authors to follow. Changes take effect on the next scan.

## Project status

Working prototype deployed. See DESIGN_DOC.md for architecture decisions.
