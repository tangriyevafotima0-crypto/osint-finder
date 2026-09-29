"""Maigret-backed implementation of SearchEngine.

Uses Maigret's real, current Python API directly (verified against the
installed maigret==0.6.4 package: `maigret.search()`, `MaigretDatabase`,
`MaigretCheckStatus`) rather than shelling out and parsing terminal output.

No Maigret-specific structures (SiteResult, MaigretSite, etc.) leak outside
this module — everything returned to the rest of the app is a plain
SearchResult.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Dict, List, Optional

from core.models import ResultStatus, SearchMode, SearchResult
from core.normalize import normalize_platform_name, normalize_profile_url
from engines.base import SearchEngine
from utils.logger import get_logger

logger = get_logger(__name__)

# How many of the most popular (lowest alexa_rank) sites Fast Search checks.
FAST_SEARCH_SITE_LIMIT = 500

# Bounded concurrency toward third-party sites during discovery.
MAX_CONCURRENT_REQUESTS = 20

# Per-request timeout (seconds) for each site check.
REQUEST_TIMEOUT = 6


class MaigretEngine(SearchEngine):
    name = "maigret"

    def __init__(self, data_file: Optional[str] = None):
        self._data_file = data_file
        self._db = None  # lazily loaded MaigretDatabase
        self._db_lock = asyncio.Lock()

    # -- internals ---------------------------------------------------

    def _default_data_file(self) -> str:
        import maigret

        pkg_dir = maigret.__file__.rsplit("/", 1)[0]
        return f"{pkg_dir}/resources/data.json"

    async def _load_database(self):
        if self._db is not None:
            return self._db

        async with self._db_lock:
            if self._db is not None:
                return self._db

            from maigret.sites import MaigretDatabase

            path = self._data_file or self._default_data_file()
            loop = asyncio.get_running_loop()
            db = await loop.run_in_executor(None, lambda: MaigretDatabase().load_from_file(path))
            self._db = db
            logger.info(f"Maigret database loaded: {len(db.sites)} sites total")
            return db

    def _select_sites(self, db, mode: SearchMode) -> Dict:
        if mode == SearchMode.DEEP:
            top = sys.maxsize
        else:
            top = FAST_SEARCH_SITE_LIMIT
        return db.ranked_sites_dict(top=top, id_type="username")

    def _to_search_result(self, username: str, site_name: str, site_result: dict) -> Optional[SearchResult]:
        from maigret.result import MaigretCheckStatus

        status_obj = site_result.get("status")
        if status_obj is None:
            return None

        maigret_status = getattr(status_obj, "status", None)
        if maigret_status != MaigretCheckStatus.CLAIMED:
            # NOT_FOUND / errored checks are not useful discovery candidates;
            # we don't surface every miss to the user (would be noisy), so
            # we simply skip them here. This keeps discovery output focused
            # on actual candidates per the "search wide, enrich narrow"
            # principle.
            return None

        profile_url = site_result.get("url_user") or site_result.get("url_main") or ""
        if not profile_url:
            return None

        platform = normalize_platform_name(site_name)

        return SearchResult(
            username=username,
            platform=platform,
            profile_url=profile_url,
            status=ResultStatus.FOUND,
            source_engines=[self.name],
            dedup_key=f"{platform.lower()}::{normalize_profile_url(profile_url)}",
        )

    # -- public API ----------------------------------------------------

    async def search(self, username: str, mode: SearchMode) -> List[SearchResult]:
        import maigret as maigret_pkg

        db = await self._load_database()
        site_dict = self._select_sites(db, mode)

        logger.info(
            f"Maigret discovery starting: mode={mode.value} sites_checked={len(site_dict)}"
        )

        maigret_logger = logging.getLogger("maigret_finder_internal")
        maigret_logger.setLevel(logging.CRITICAL)

        try:
            raw_results = await maigret_pkg.search(
                username=username,
                site_dict=site_dict,
                logger=maigret_logger,
                timeout=REQUEST_TIMEOUT,
                max_connections=MAX_CONCURRENT_REQUESTS,
                no_progressbar=True,
                id_type="username",
                is_parsing_enabled=False,
            )
        except Exception as exc:  # noqa: BLE001 - discovery must never crash the app
            logger.error(f"Maigret discovery failed: {exc}")
            return []

        results: List[SearchResult] = []
        for site_name, site_result in raw_results.items():
            try:
                normalized = self._to_search_result(username, site_name, site_result)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Failed to normalize result for {site_name}: {exc}")
                continue
            if normalized:
                results.append(normalized)

        logger.info(f"Maigret discovery completed: {len(results)} candidate(s) found")
        return results
