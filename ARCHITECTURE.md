# Architecture

## Module responsibilities

| Module | Responsibility |
|---|---|
| `core/models.py` | Lightweight typed data (`SearchResult`, `SearchMetrics`, `SearchResponse`, enums). No raw HTML/cookies/auth data ever stored. |
| `core/normalize.py` | Username and profile-URL normalization (Phase 1: obvious formats only, no mutation engine). |
| `core/priority.py` | Configurable HIGH/MEDIUM/LOW platform tiers. |
| `core/aggregator.py` | Deduplication by `platform + normalized URL`. |
| `core/scorer.py` | Confidence scoring (0–100, relevance not identity) and ranking. |
| `core/cache.py` | Search-result cache with TTL (fast: 30 min, deep: 60 min) and corruption handling. |
| `core/search_manager.py` | The **only** orchestrator of the full pipeline. GUI never talks to engines/enrichment directly. |
| `engines/base.py` | Abstract `SearchEngine` interface. |
| `engines/maigret_engine.py` | Maigret integration, verified against the installed Maigret 0.6.4 Python API. No Maigret-specific types leak outside this file. |
| `enrichment/avatar.py` | Lazy avatar download, size/dimension limits, disk cache, thumbnailing. |
| `enrichment/profile.py` | Generic public-metadata (og:title/description/image) enrichment. |
| `enrichment/instagram.py` | Instagram-priority enrichment path (currently reuses `profile.py`; separate module so Phase 2 can specialize it). |
| `gui/*` | PySide6 UI. `workers.py` runs `SearchManager` on a background `QThread` so the GUI thread never blocks. |
| `utils/*` | Logging, filesystem paths (`~/Library/Application Support/OSINT Finder/`), HTTP client, OS/arch detection. |

## Data flow (search pipeline)

```
USER INPUT
  -> normalize_username()
  -> is_valid_username() check
  -> cache.load() [TTL: 30min fast / 60min deep]
       HIT  -> return cached results immediately
       MISS -> continue
  -> MaigretEngine.search(username, mode)
       Fast:  ranked_sites_dict(top=500)   (alexa-rank popular sites)
       Deep:  ranked_sites_dict(top=all)   (full current Maigret database)
  -> deduplicate()  [platform + normalized URL]
  -> apply_scores() + rank_results()
  -> GUI shown discovered results (progressive)
  -> select up to MAX_ENRICH=8 candidates
       priority: Instagram first, then HIGH-tier platforms, then confidence
  -> enrich selected candidates (profile.py / instagram.py)
       -> lazy avatar fetch only for enriched candidates (avatar.py)
  -> re-score, re-rank
  -> cache.save()
  -> GUI updates enriched cards
```

## Engine interface

`SearchEngine.search(username, mode) -> list[SearchResult]` is the only
contract. `MaigretEngine` is the sole Phase 1 implementation. Future
engines (`SherlockEngine`, `InstagramEngine`, `GitHubEngine`,
`RedditEngine`) can be added by implementing this interface and
registering with `SearchManager` — no GUI or `SearchManager` rewrite
needed.

## Cache rules

- One JSON file per `(username, mode)` under `cache/search/`.
- Fast search TTL: 30 minutes. Deep search TTL: 60 minutes.
- Corrupted/unreadable/incompatible cache files are deleted and treated
  as a miss — never raise.
- `Refresh` bypasses the cache (`force_refresh=True`).

## Enrichment rules

- Discovery never enriches every result — only up to `MAX_ENRICH` (default
  8) candidates, selected by: Instagram first, then HIGH-tier platforms,
  then confidence score.
- Avatars are fetched lazily, only for enriched candidates, and only if a
  public avatar URL was found. Max 1 retry. Max 256KB / 1024×1024.
- Enrichment never attempts login, CAPTCHA bypass, rate-limit evasion, or
  private-account access. Any failure falls back to the original
  (unenriched) result — enrichment never removes a discovered candidate.

## Safety boundaries (see also README § Ethical Scope)

- No credential handling, no session/cookie theft, no CAPTCHA bypass, no
  proxy rotation for evasion, no scraping of authenticated/private content.
- If a platform blocks a request (403, rate limit, etc.), the result is
  simply treated as unavailable — never retried aggressively, never
  circumvented.
