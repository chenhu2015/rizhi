# rizhi — daily paper scan

You are running the daily paper digest for rizhi (日知). Complete every step below in order. Do not stop early unless step 1 returns an empty list.

---

## Step 1: Fetch today's papers

```bash
cd ~/rizhi
~/.venv/bin/python -m scanner.fetch > /tmp/rizhi_papers.json
cat /tmp/rizhi_papers.json
```

Read the JSON array. If it is empty (`[]`), print "No new papers today." and stop — do not proceed to further steps.

---

## Step 2: Load the interest profile

Read `scanner/interest_profile.yaml`. This is your scoring guide.

---

## Step 3: Score each paper

For every paper in the JSON array:

1. Read the `title` and `abstract` fields carefully.
2. Assign a `score` from 0.0 to 1.0 based on how well the paper matches the topics and keywords in the interest profile.
   - 0.9–1.0: directly advances the user's core research interests
   - 0.7–0.9: clearly relevant, useful to know about
   - below 0.7: tangential or unrelated — exclude from output
3. For papers scoring >= `min_score` (default 0.7):
   - Write a 2–3 sentence English summary focusing on the key contribution and method
   - List which topics/keywords from the interest profile it matches

---

## Step 4: Write results files

Create two files with identical content — today's dated file and `latest.json`:

**File paths:**
- `~/rizhi/results/YYYY-MM-DD.json`  (use today's actual date)
- `~/rizhi/results/latest.json`

**Format** — an array of scored papers (only those >= min_score), sorted by score descending, capped at `max_papers_per_run`:

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

## Step 5: Write Obsidian vault notes

For each paper in the results (score >= min_score):

**File path:** `~/papers-vault/papers/YYYY/MM/YYYY-MM-DD-<slug>.md`

Where `<slug>` is the paper title lowercased, spaces replaced with hyphens, special characters removed, truncated to 60 characters.

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

<1–2 sentences explaining why this matches the user's current research interests>

## My Thoughts

<!-- Add your own notes here -->
```

---

## Step 6: Write daily digest note

**File path:** `~/papers-vault/digests/YYYY-MM-DD.md`

```markdown
# Digest: YYYY-MM-DD

<N> paper(s) found today.

<for each paper, one line:>
- [[YYYY-MM-DD-<slug>]] — score: <score> — <one-sentence description>

<if no papers:>
No papers met the score threshold today.
```

---

## Step 7: Commit and push vault

```bash
cd ~/papers-vault
git pull --rebase origin main
git add papers/ digests/
git commit -m "digest: YYYY-MM-DD (N papers)" || echo "nothing to commit"
git push origin main
```

Replace `N` with the actual number of papers added.

---

## Step 8: Notify the server

```bash
curl -s -X POST http://localhost:8000/internal/notify
```

This triggers Web Push notifications to the user's phone. If the server is not running, the curl will fail silently — that is acceptable.

---

## Summary checklist

- [ ] Fetched papers
- [ ] Scored all papers against interest profile
- [ ] Wrote `results/YYYY-MM-DD.json` and `results/latest.json`
- [ ] Wrote one vault note per qualifying paper
- [ ] Wrote daily digest note
- [ ] Committed and pushed vault
- [ ] Notified server
