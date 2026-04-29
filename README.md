# rizhi (日知)

> 日知其所亡 — Know daily what you did not know before. *(Analects of Confucius)*

A 24/7 research paper scout running on an OCI VM. It scans arxiv and academic sources daily, scores papers against your interest profile using Claude, and delivers a curated digest to your phone via Claude Code Remote Control.

## What it does

- Fetches new papers daily from arxiv and Semantic Scholar
- Scores each paper for relevance using Claude Code (Pro/Max — no separate API key needed)
- Pushes a notification to your phone when high-scoring papers are found
- Tap the notification → connect to the remote Claude session → read summaries and ask questions

## Current interest areas

- Reinforcement learning / agentic RL training
- Multimodal models / vision-language models (VLM)

## Stack

- Python 3.12
- Claude Code (agent, Pro/Max subscription)
- arxiv API + Semantic Scholar API (both free)
- SQLite (deduplication)
- systemd (OCI Ubuntu 22.04 deployment)
- Ollama (planned: cheaper pre-filtering)

## Project status

Design phase. Implementation in progress.
