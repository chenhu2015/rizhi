# rizhi — daily paper hunt

You are the research agent for rizhi (日知). Your job is not just to fetch and score papers — it is to *think* about what is worth searching for today, run targeted searches, and build a progressively more personalised digest over time.

Work through the steps below in order.

---

## Step 0: Orient yourself

Before searching, understand the current state of the user's research.

**Read the interest profile:**
```
~/claude-project/rizhi/scanner/interest_profile.yaml
```

**Scan recent vault digests** (last 7 days, skip if directory is empty):
```
~/claude-project/papers-vault/digests/
```

**Skim recent vault notes for user annotations** — look specifically for content the user has written under `## My Thoughts` in any paper notes:
```
~/claude-project/papers-vault/papers/
```

Based on what you find, answer these questions mentally before moving on:
1. What topics have been well-covered recently? (de-prioritise retreading)
2. Which papers did the user annotate or seem engaged with? (go deeper on those threads)
3. What adjacent or emerging areas might be worth exploring today that haven't appeared yet?
4. Are there specific authors, techniques, or open problems that keep coming up?

---

## Step 2: Plan today's searches

Based on your orientation, decide on **2–4 specific search queries** for today. Write your plan as a brief note in your response before executing — this makes the digest more useful and your reasoning transparent.

Rules for good queries:
- Be specific, not broad. `"agentic RL tool use grounding"` beats `"reinforcement learning"`.
- Vary the angle across queries — different facets of the user's interests, not the same topic rephrased.
- If the user's annotations pointed toward a thread, follow it.
- arxiv query syntax: `ti:` for title search, `all:` for full text, `AND`/`OR` for combining terms. Example: `ti:reward model AND (ti:efficiency OR ti:training)`.

---

## Step 3: Execute searches

For each query in your plan, run:

```bash
cd ~/claude-project/rizhi
~/.venv/bin/python -m scanner.search "YOUR QUERY HERE" --max 30
```

You may also target a specific source:
```bash
~/.venv/bin/python -m scanner.search "YOUR QUERY HERE" --source arxiv --max 30
~/.venv/bin/python -m scanner.search "YOUR QUERY HERE" --source s2 --max 20
```

Each call returns a JSON array of **unseen** papers (already-seen papers are filtered out automatically). Collect all results across your queries.

If a search returns `[]`, note it but continue — move on to the next query.

---

## Step 4: Score and summarise

For every paper collected across all searches:

1. Read the `title` and `abstract` carefully.
2. Assign a `score` from 0.0 to 1.0 based on how well it matches the interest profile and the specific threads you identified in Step 0:
   - 0.9–1.0: directly advances the user's core research interests
   - 0.7–0.9: clearly relevant, useful to know about
   - below 0.7: tangential — exclude from output
3. For papers scoring ≥ `min_score` (from the interest profile, default 0.7):
   - Write a 2–3 sentence English summary focusing on key contribution and method
   - List which topics/keywords from the interest profile it matches

Deduplicate: if the same paper appeared in multiple search results, keep it once with the highest score.

---

## Step 5: Write results files

Create two files with identical content — today's dated file and `latest.json`.

**File paths:**
- `~/claude-project/rizhi/results/YYYY-MM-DD.json`
- `~/claude-project/rizhi/results/latest.json`

**Format** — array of scored papers (only those ≥ min_score), sorted by score descending, capped at `max_papers_per_run` from the interest profile:

```json
[
  {
    "id": "2404.12345",
    "title": "Paper Title Here",
    "authors": ["Author A", "Author B"],
    "url": "https://arxiv.org/abs/2404.12345",
    "published": "2026-04-29",
    "source": "arxiv",
    "score": 0.91,
    "summary": "2–3 sentence summary written by you.",
    "matched_topics": ["agentic RL", "reward model"]
  }
]
```

If no papers meet the threshold, write `[]` to both files.

---

## Step 6: Write Obsidian vault notes

For each paper in the results (score ≥ min_score):

**File path:** `~/claude-project/papers-vault/papers/YYYY/MM/YYYY-MM-DD-<slug>.md`

Where `<slug>` is the paper title lowercased, spaces replaced with hyphens, special characters removed, truncated to 60 characters.

```bash
mkdir -p ~/claude-project/papers-vault/papers/YYYY/MM
```

**Template:**

```markdown
---
title: "<full title>"
authors: [<comma-separated quoted names>]
date: YYYY-MM-DD
arxiv_id: "<id>"
url: "<url>"
score: <score>
topics: [<matched topics as unquoted yaml list>]
status: unread
---

# <full title>

## Summary

<your 2–3 sentence summary>

## Key Contributions

<bullet list of 2–4 key contributions based on the abstract>

## Relevance

<1–2 sentences explaining why this matches the user's current research interests, referencing any thread or annotation from Step 0 that led you here>

## My Thoughts

<!-- Add your own notes here -->
```

---

## Step 7: Write daily digest note

**File path:** `~/claude-project/papers-vault/digests/YYYY-MM-DD.md`

```markdown
# Digest: YYYY-MM-DD

<N> paper(s) found today.

## Search plan

<paste your search plan from Step 2 — queries you ran and why>

## Papers

<for each paper, one line:>
- [[YYYY-MM-DD-<slug>]] — score: <score> — <one-sentence description>

<if no papers:>
No papers met the score threshold today.
```

Including the search plan in the digest makes it easy to see over time how your searches evolved.

---

## Step 8: Commit and push vault

```bash
cd ~/claude-project/papers-vault
git pull --rebase origin main
git add papers/ digests/
git commit -m "digest: YYYY-MM-DD (N papers)" || echo "nothing to commit"
git push origin main
```

Replace `N` with the actual number of papers added.

---

## Step 9: Notify the server

```bash
curl -s -X POST http://localhost:8000/internal/notify
```

This triggers Web Push notifications to the user's phone. If the server is not running, the curl will fail silently — that is acceptable.

---

## Summary checklist

- [ ] Read interest profile + recent vault notes
- [ ] Planned 2–4 targeted search queries
- [ ] Ran searches and collected results
- [ ] Scored all papers against interest profile
- [ ] Wrote `results/YYYY-MM-DD.json` and `results/latest.json`
- [ ] Wrote one vault note per qualifying paper
- [ ] Wrote daily digest note (including search plan)
- [ ] Committed and pushed vault
- [ ] Notified server
