"""Abstract interface every discovery engine must implement.

Phase 1 ships MaigretEngine only. This interface exists so future engines
(SherlockEngine, InstagramEngine, GitHubEngine, RedditEngine, ...) can be
added without touching the GUI or SearchManager.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.models import SearchMode, SearchResult


class SearchEngine(ABC):
    """Common interface for any username discovery engine."""

    #: Short machine-readable name used in SearchResult.source_engines
    name: str = "base"

    @abstractmethod
    async def search(self, username: str, mode: SearchMode) -> List[SearchResult]:
        """Discover public profile candidates for a username.

        Implementations must:
        - never raise on individual site failures (log and skip instead)
        - never attempt to bypass authentication, CAPTCHAs, or rate limits
        - return already-normalized SearchResult objects
        """
        raise NotImplementedError
