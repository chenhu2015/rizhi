# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

**rizhi (日知)** — A daily research paper digest service. Scans arxiv and academic sources, scores papers using Claude Code, and delivers push notifications to the user's phone via Claude Code Remote Control.

## Language

All documents and code comments in this project are in **English**.

## Stack

- **Language:** Python 3.12
- **Agent:** Claude Code (Pro/Max subscription, no separate API key)
- **Sources:** arxiv API, Semantic Scholar API
- **Storage:** SQLite
- **Deployment:** Ubuntu 22.04 LTS on OCI VM, systemd service
- **Future:** Ollama for cheap pre-filtering subtasks

## Project Structure

```
rizhi/
├── scanner/
│   ├── arxiv_client.py         # arxiv API queries
│   ├── web_client.py           # Semantic Scholar / RSS feeds
│   ├── scorer.py               # relevance scoring via Claude Code agent
│   └── interest_profile.yaml   # user interest configuration (edit this to change topics)
├── agent/
│   └── CLAUDE.md               # instructions for the OCI Claude Code session
├── storage/
│   └── seen_papers.db          # SQLite, prevents duplicate notifications
├── deploy/
│   ├── rizhi.service           # systemd unit file
│   └── setup.sh                # one-shot OCI setup script
├── config.yaml                 # scan schedule, sources, score threshold
├── requirements.txt
├── README.md
└── DESIGN_DOC.md
```

## OCI VM

- **Host:** OCI-Desktop (SSH alias configured)
- **OS:** Ubuntu 22.04 LTS
- **User:** ubuntu
- **Claude Code:** installed at `~/.cache/claude/staging/.../claude`

## Key Config Files

- `scanner/interest_profile.yaml` — topics, keywords, authors, score threshold
- `config.yaml` — scan interval, max papers per run, notification settings
