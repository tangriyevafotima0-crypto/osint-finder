"""SearchManager: the only orchestrator of the full search pipeline.

USER INPUT -> normalize -> cache check -> discovery -> normalize results ->
dedup -> rank -> confidence -> select enrichment budget -> enrich selected
-> return to GUI.

The GUI must never call engines or enrichment directly — only this class.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable, List, Optional

import core.cache as cache
from core.aggregator import deduplicate
from core.models import (
    SearchMetrics,
    SearchMode,
    SearchResponse,
    SearchResult,
    SearchState,
)
from core.normalize import is_valid_username, normalize_username
from core.priority import is_instagram, platform_tier, TIER_HIGH
from core.scorer import apply_scores, rank_results
from engines.maigret_engine import MaigretEngine
from enrichment.avatar import fetch_avatar
from enrichment.instagram import enrich_instagram
from enrichment.profile import enrich_profile
from utils.logger import get_logger

logger = get_logger("search_manager")

MAX_ENRICH = 8


class SearchCancelled(Exception):
    """Raised internally when a search is cancelled mid-flight."""


class SearchManager:
    def __init__(self, max_enrich: int = MAX_ENRICH):
        self.max_enrich = max_enrich
        self._engine = MaigretEngine()
        self._cancel_event: Optional[asyncio.Event] = None

    def cancel(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()

    async def search(
        self,
        raw_username: str,
        mode: SearchMode = SearchMode.FAST,
        force_refresh: bool = False,
        on_state_change: Optional[Callable[[SearchState, dict], None]] = None,
        on_partial_results: Optional[Callable[[List[SearchResult]], None]] = None,
    ) -> SearchResponse:
        """Run the full pipeline. Safe to await from a background worker thread."""

        self._cancel_event = asyncio.Event()
        start_time = time.monotonic()
        metrics = SearchMetrics()

        def notify(state: SearchState, **extra):
            if on_state_change:
                on_state_change(state, extra)

        username = normalize_username(raw_username)
        if not is_valid_username(username):
            notify(SearchState.ERROR, message="Invalid username")
            return SearchResponse(
                username=raw_username, mode=mode, results=[], metrics=metrics, state=SearchState.ERROR
            )

        notify(SearchState.SEARCHING)

        if not force_refresh:
            cached = cache.load(username, mode)
            if cached is not None:
                logger.info(f"Cache HIT for {username} ({mode.value})")
                metrics.cache_hit = True
                metrics.results_found = len(cached)
                metrics.results_unique = len(cached)
                metrics.results_enriched = sum(1 for r in cached if r.enriched)
                metrics.total_time = time.monotonic() - start_time
                notify(SearchState.SUCCESS if cached else SearchState.NO_RESULTS)
                return SearchResponse(
                    username=username, mode=mode, results=cached, metrics=metrics, state=SearchState.SUCCESS
                )

        logger.info(f"Cache MISS for {username} ({mode.value})")

        try:
            # -- Discovery --------------------------------------------------
            discovery_start = time.monotonic()
            raw_results = await self._engine.search(username, mode)
            metrics.discovery_time = time.monotonic() - discovery_start
            metrics.results_found = len(raw_results)

            if self._cancel_event.is_set():
                notify(SearchState.CANCELLED)
                return self._cancelled_response(username, mode, metrics)

            # -- Dedup --------------------------------------------------------
            dedup_start = time.monotonic()
            unique_results = deduplicate(raw_results)
            metrics.deduplication_time = time.monotonic() - dedup_start
            metrics.results_unique = len(unique_results)

            # -- Score + rank ---------------------------------------------
            apply_scores(unique_results, username)
            ranked = rank_results(unique_results)

            notify(SearchState.DISCOVERY_COMPLETE, found=len(ranked))
            if on_partial_results:
                on_partial_results(ranked)

            if not ranked:
                metrics.total_time = time.monotonic() - start_time
                notify(SearchState.NO_RESULTS)
                cache.save(username, mode, ranked)
                return SearchResponse(
                    username=username, mode=mode, results=ranked, metrics=metrics, state=SearchState.NO_RESULTS
                )

            # -- Enrichment budget --------------------------------------------
            enrichment_start = time.monotonic()
            candidates = self._select_enrichment_candidates(ranked)
            notify(SearchState.ENRICHING, count=len(candidates))

            await self._enrich_candidates(candidates)
            metrics.enrichment_time = time.monotonic() - enrichment_start
            metrics.results_enriched = sum(1 for r in ranked if r.enriched)

            if self._cancel_event.is_set():
                notify(SearchState.CANCELLED)
                return self._cancelled_response(username, mode, metrics, ranked)

            # Re-score after enrichment (avatar/metadata bonuses may now apply)
            apply_scores(ranked, username)
            ranked = rank_results(ranked)

            metrics.total_time = time.monotonic() - start_time
            cache.save(username, mode, ranked)

            notify(SearchState.SUCCESS)
            logger.info(
                f"Search completed for {username} in {metrics.total_time:.1f}s "
                f"(found={metrics.results_found}, unique={metrics.results_unique}, "
                f"enriched={metrics.results_enriched})"
            )
            return SearchResponse(
                username=username, mode=mode, results=ranked, metrics=metrics, state=SearchState.SUCCESS
            )

        except Exception as exc:  # noqa: BLE001 - search must never crash the app
            logger.error(f"Search failed for {username}: {exc}")
            notify(SearchState.ERROR, message=str(exc))
            metrics.total_time = time.monotonic() - start_time
            return SearchResponse(
                username=username, mode=mode, results=[], metrics=metrics, state=SearchState.ERROR
            )

    # -- internals -------------------------------------------------------

    def _cancelled_response(self, username, mode, metrics, results=None) -> SearchResponse:
        metrics.total_time = metrics.total_time or 0.0
        return SearchResponse(
            username=username, mode=mode, results=results or [], metrics=metrics, state=SearchState.CANCELLED
        )

    def _select_enrichment_candidates(self, ranked: List[SearchResult]) -> List[SearchResult]:
        """Pick up to max_enrich results to enrich.

        Priority: Instagram first, then other HIGH priority platforms,
        then highest confidence overall (ranked is already sorted this way,
        modulo Instagram getting pulled to the very front).
        """
        instagram = [r for r in ranked if is_instagram(r.platform)]
        rest = [r for r in ranked if not is_instagram(r.platform)]
        ordered = instagram + rest  # ranked is already confidence + tier sorted
        return ordered[: self.max_enrich]

    async def _enrich_candidates(self, candidates: List[SearchResult]) -> None:
        for result in candidates:
            if self._cancel_event and self._cancel_event.is_set():
                break
            try:
                if is_instagram(result.platform):
                    await enrich_instagram(result)
                else:
                    await enrich_profile(result)

                if result.avatar_url:
                    avatar_path = await fetch_avatar(result.avatar_url)
                    if avatar_path:
                        result.avatar_path = avatar_path

                result.enriched = True
            except Exception as exc:  # noqa: BLE001 - one bad candidate must not stop the rest
                logger.debug(f"Enrichment failed for {result.profile_url}: {exc}")
                # Keep original (unenriched) result rather than dropping it.
                continue
