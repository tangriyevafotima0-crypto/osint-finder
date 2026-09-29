"""Lightweight normalized data models for OSINT Finder.

These models intentionally avoid storing raw HTML, cookies, or any
authentication data. They exist purely to represent public, discoverable
profile information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class ResultStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class SearchMode(str, Enum):
    FAST = "fast"
    DEEP = "deep"


class SearchState(str, Enum):
    IDLE = "IDLE"
    SEARCHING = "SEARCHING"
    DISCOVERY_COMPLETE = "DISCOVERY_COMPLETE"
    ENRICHING = "ENRICHING"
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class ConfidenceLabel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


def confidence_label(score: int) -> ConfidenceLabel:
    if score >= 80:
        return ConfidenceLabel.HIGH
    if score >= 50:
        return ConfidenceLabel.MEDIUM
    return ConfidenceLabel.LOW


@dataclass
class SearchResult:
    """A single normalized, deduplicated public profile candidate."""

    username: str
    platform: str
    profile_url: str
    status: ResultStatus = ResultStatus.FOUND
    title: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_path: Optional[str] = None
    confidence: int = 0
    confidence_label: ConfidenceLabel = ConfidenceLabel.LOW
    source_engines: List[str] = field(default_factory=list)
    found_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Internal bookkeeping (not shown to user, not serialized as "content")
    dedup_key: Optional[str] = None
    enriched: bool = False

    def to_json(self) -> dict:
        return {
            "username": self.username,
            "platform": self.platform,
            "profile_url": self.profile_url,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "avatar_url": self.avatar_url,
            "avatar_path": self.avatar_path,
            "confidence": self.confidence,
            "confidence_label": self.confidence_label.value,
            "source_engines": list(self.source_engines),
            "found_at": self.found_at.isoformat(),
            "enriched": self.enriched,
        }

    @staticmethod
    def from_json(data: dict) -> "SearchResult":
        found_at = data.get("found_at")
        try:
            found_at_dt = datetime.fromisoformat(found_at) if found_at else datetime.now(timezone.utc)
        except ValueError:
            found_at_dt = datetime.now(timezone.utc)
        return SearchResult(
            username=data["username"],
            platform=data["platform"],
            profile_url=data["profile_url"],
            status=ResultStatus(data.get("status", "FOUND")),
            title=data.get("title"),
            description=data.get("description"),
            avatar_url=data.get("avatar_url"),
            avatar_path=data.get("avatar_path"),
            confidence=data.get("confidence", 0),
            confidence_label=ConfidenceLabel(data.get("confidence_label", "Low")),
            source_engines=list(data.get("source_engines", [])),
            found_at=found_at_dt,
            enriched=data.get("enriched", False),
        )


@dataclass
class SearchMetrics:
    discovery_time: float = 0.0
    deduplication_time: float = 0.0
    enrichment_time: float = 0.0
    total_time: float = 0.0
    results_found: int = 0
    results_unique: int = 0
    results_enriched: int = 0
    cache_hit: bool = False


@dataclass
class SearchResponse:
    """What SearchManager hands back to the GUI."""

    username: str
    mode: SearchMode
    results: List[SearchResult]
    metrics: SearchMetrics
    state: SearchState
