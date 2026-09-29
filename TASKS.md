# Tasks

## Current task
Phase 1 build complete. Awaiting real macOS run + PyInstaller packaging
(cannot be performed in the Linux sandbox this project was built in).

## Completed
- [x] Inspected installed Maigret (0.6.4) API directly; verified `maigret.search()`,
      `MaigretDatabase.ranked_sites_dict()`, `MaigretCheckStatus` live in-sandbox.
- [x] Project structure
- [x] `core/models.py` — SearchResult, SearchMetrics, SearchResponse, enums
- [x] `engines/base.py` — SearchEngine abstraction
- [x] `engines/maigret_engine.py` — direct Python API integration (no subprocess/parsing)
- [x] Username/URL normalization + tests
- [x] Deduplication + tests (verified 27→21 example from spec)
- [x] Confidence scoring + ranking + tests
- [x] Cache (TTL, corruption handling) + tests
- [x] `SearchManager` full pipeline + tests (enrichment budget, Instagram priority,
      cache hit/miss, force refresh, engine-exception resilience, invalid input)
- [x] Avatar lazy download/cache/size-limits/thumbnailing
- [x] Generic + Instagram profile enrichment (og:tag based, fail-soft)
- [x] PySide6 GUI (main window, search bar, result cards)
- [x] Background QThread worker — fixed a real thread-teardown race found
      during headless smoke testing (see below)
- [x] GUI wired to SearchManager via worker signals
- [x] `run.sh` — actually executed end-to-end in-sandbox (venv creation,
      real `pip install` from PyPI, verification, diagnostics, idempotency
      re-run) — all passed
- [x] `scripts/bootstrap.py --diagnose` — actually executed, all checks OK
- [x] `install.bat` / `run.bat`
- [x] Full test suite: 36/36 passing
- [x] README, ARCHITECTURE.md, this file

## Known issues / limitations
- **Not run on real macOS.** Built in a Linux sandbox with no display
  server. `run.sh`'s setup logic was fully executed and verified there;
  the GUI itself was verified via `QT_QPA_PLATFORM=offscreen` construction
  and a mocked-search smoke test, not a real on-screen session.
- **PyInstaller packaging not performed.** See README § Packaging for the
  build command to run locally on macOS; untested in this environment.
- Maigret's discovery requests could not be validated against live target
  sites from this sandbox (network egress is restricted to package
  registries). The integration code path was verified against Maigret's
  real API and returned correctly-shaped results (including graceful
  403 handling) when pointed at real sites during development.
- No `.icns` icon is bundled (spec marks this optional for development).

## Bugs found and fixed during development
- `gui/workers.py` + `gui/main_window.py`: a `QThread` could be garbage
  collected while its underlying OS thread was still shutting down,
  crashing the app (`QThread: Destroyed while thread '' is still
  running`). Fixed by having `MainWindow._retire_thread()` call
  `thread.quit(); thread.wait()` before releasing the reference, and
  removing the redundant/racing `deleteLater` auto-wiring from
  `start_search()`.

## Next task (Phase 2, not in scope now)
- SherlockEngine as secondary verification
- Username variant/mutation generator
- `.icns` icon + PyInstaller `.app` build verified on real macOS hardware
