---
name: mustang-research
description: Find viral Ford Mustang reels/posts on Instagram by hashtag (via Apify), score their viral potential and prepare credited repost candidates for @mustangemotion. Use when asked to find, review or change the daily Mustang candidates.
---

# Mustang research

Adapted from `instagram-research` (bradautomates/head-of-content): searches by hashtag instead of a fixed
account list, scores by engagement velocity, and prepares repost candidates with credit to the author.

## Where it runs

Daily in GitHub Actions (`.github/workflows/daily-research.yml`), because the Apify API is not reachable
from the Claude workspace. `APIFY_TOKEN` lives only as a repository secret — never write it to a file.
Run it by hand from GitHub: Actions → "Recerca diària de candidats" → Run workflow.

## Pipeline

1. `scripts/fetch_hashtags.py` — `apify/instagram-hashtag-scraper`, rotating `hashtags_per_day` of the
   hashtags in `config/sources.json`, `results_per_hashtag` each.
2. `scripts/select_candidates.py` — scores and filters, downloads the media to `media/<date>/` (public raw
   URL for the Instagram API) and writes `data/candidates/<date>.json`.

## Scoring

- engagement = likes + 3 × comments + 0.1 × views
- velocity = engagement / (hours since posting + 2) ^ 0.8 — candidates are ranked by velocity
- Filtered out: already published (`data/history.json`), same author within
  `min_days_between_same_author` days, older than `max_age_days`, `excluded_authors`, our own account,
  and more than one candidate per author.

## Captions

Every caption starts with `🎥 @author` (credit is mandatory). When reviewing candidates, Claude may
rewrite the `caption` field in English for a US audience: one short hook about the car, the credit line,
the follow/tag call to action, and the hashtags. Never remove the credit or claim the content as ours.

## Approval and publishing

Every candidate needs Pol's approval before it is published. No exceptions.

- `scripts/telegram_send.py` sends each candidate (video/photo + stats + caption) with ✅/❌ buttons.
- `.github/workflows/bot.yml` runs every 10 min: `telegram_poll.py` records the answers in the
  candidate file (`status`: pending → approved/rejected) and learns the chat id from `/start`;
  `publish.py`, at each `publish_times` slot (America/New_York, up to 90 min late), sends the oldest
  approved candidate to the Make webhook (`MAKE_WEBHOOK_URL`), which publishes it with the official
  Instagram API (`make/publicar-instagram.blueprint.json`). Then it is marked `published` and appended
  to `data/history.json`.
- Secrets: `APIFY_TOKEN`, `TELEGRAM_BOT_TOKEN`, `MAKE_WEBHOOK_URL` — repository secrets only.

## Cost

Apify charges per result (≈ $1.90 per 1,000 for the hashtag scraper). Defaults (3 hashtags × 20 reels a day)
stay under the free monthly credit; raise `hashtags_per_day` or `results_per_hashtag` with care.
