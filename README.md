# OSINT Finder

A fast, lightweight macOS desktop tool for discovering **public** social
media/website profiles associated with a username, using
[Maigret](https://github.com/soxoj/maigret) for discovery, with selective
enrichment of the most relevant results.

## Features

- Enter a username → discover public profiles across hundreds (Fast) or
  thousands (Deep) of sites
- Automatic deduplication and relevance ranking (not identity verification)
- Only the top ~8 most relevant results are enriched with public
  metadata/avatar — not every discovered profile
- Instagram results get enrichment priority when found
- Search result and avatar caching (30 min fast / 60 min deep TTL)
- Progressive results — see discovered profiles immediately, watch them
  get enriched in real time
- Responsive GUI — search runs on a background thread, never blocks the UI
- Cancel support, refresh-to-bypass-cache

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full module map and data
flow. In short:

```
GUI → SearchManager → MaigretEngine → Maigret
```

The GUI never talks to Maigret directly, and the app is built so
additional discovery engines (Sherlock, etc.) can be added later without
rewriting the GUI or SearchManager.

## macOS installation (quick start)

```bash
chmod +x run.sh
./run.sh
```

This will detect your Python installation, create a virtual environment,
install dependencies, verify everything, and launch the app. It's safe to
run repeatedly — it won't redo work that's already done.

If Python isn't installed, the script will tell you whether Homebrew is
available and how to proceed. It never installs anything globally and
never uses `sudo pip install`.

## Windows installation

```
install.bat
run.bat
```

`run.bat` will automatically call `install.bat` on first run if no virtual
environment exists yet.

## Development setup (manual)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Running diagnostics

```bash
python3 scripts/bootstrap.py --diagnose
```

Reports OS, architecture, Python version, virtual environment status, and
whether PySide6 / Maigret / httpx / Pillow / cache directories / internet
connectivity are all OK. Does not perform an actual OSINT search.

## Testing

```bash
pip install -r requirements.txt  # includes pytest, pytest-asyncio
python3 -m pytest tests/ -v
```

Tests mock Maigret, HTTP requests, and avatar downloads — no live network
calls or real site scanning happen during the test suite.

## Packaging (PyInstaller)

Run this on macOS, on the architecture you're targeting (Apple Silicon or
Intel — PyInstaller does not cross-compile):

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --windowed --name "OSINT Finder" \
    --add-data "resources:resources" \
    main.py
```

The resulting `dist/OSINT Finder.app` is self-contained and does not
require the `.venv` or Terminal to run. It uses the user's
`~/Library/Application Support/OSINT Finder/` directory for cache/config,
regardless of where the `.app` itself is installed.

To add a custom icon, place an `.icns` file in `resources/icons/` and add
`--icon resources/icons/your-icon.icns` to the command above. An icon is
optional — the app works without one.

## Limitations

- Phase 1 only integrates Maigret. Sherlock and other engines are planned
  but not implemented (see `engines/base.py` for the extension point).
- No username mutation/variant generation — only obvious input formats
  (e.g. `@handle`, common profile URLs) are normalized.
- No reverse image search, face recognition, or graph-based investigation.
- Confidence scores are a **relevance ranking**, not identity verification.
  A high score means "this looks like the account you searched for," not
  "this is confirmed to be the same person."

## Ethical scope

OSINT Finder only works with **publicly accessible** information:

- public username discovery across sites
- public profile URLs
- publicly accessible metadata and avatar images

It never attempts password cracking, credential stuffing, account
takeover, session/cookie theft, CAPTCHA bypass, rate-limit bypass,
authentication bypass, or scraping of private/authenticated content. If a
platform blocks a request, the app respects that and shows a placeholder
or omits the field — it never tries to circumvent platform security.

## Future roadmap

Not implemented in Phase 1, but the architecture supports adding later
without rewriting the GUI, `SearchManager`, `SearchResult`, or cache:

- `SherlockEngine` as a secondary verification pass
- Username variant/mutation generation
- Reverse image search
- Graph-based investigation view

These are explicitly out of scope for this phase.
