from core.aggregator import deduplicate
from core.models import SearchResult


def make_result(platform, url, engine="maigret", **kwargs):
    return SearchResult(
        username=kwargs.pop("username", "john"),
        platform=platform,
        profile_url=url,
        source_engines=[engine],
        **kwargs,
    )


def test_dedup_same_platform_and_url_variants():
    results = [
        make_result("Instagram", "https://instagram.com/john"),
        make_result("Instagram", "https://www.instagram.com/john/"),
    ]
    deduped = deduplicate(results)
    assert len(deduped) == 1
    assert deduped[0].platform == "Instagram"


def test_dedup_merges_source_engines():
    results = [
        make_result("GitHub", "https://github.com/john", engine="maigret"),
        make_result("GitHub", "https://github.com/john", engine="sherlock"),
    ]
    deduped = deduplicate(results)
    assert len(deduped) == 1
    assert set(deduped[0].source_engines) == {"maigret", "sherlock"}


def test_dedup_distinct_platforms_not_merged():
    results = [
        make_result("Instagram", "https://instagram.com/john"),
        make_result("GitHub", "https://github.com/john"),
    ]
    deduped = deduplicate(results)
    assert len(deduped) == 2


def test_dedup_fills_missing_metadata():
    a = make_result("GitHub", "https://github.com/john", title=None)
    b = make_result("GitHub", "https://github.com/john", title="John Smith")
    deduped = deduplicate([a, b])
    assert len(deduped) == 1
    assert deduped[0].title == "John Smith"


def test_27_results_dedupe_to_21_unique():
    # Simulates spec's example: 27 discovered -> 21 unique.
    results = []
    for i in range(15):
        results.append(make_result(f"Site{i}", f"https://site{i}.com/john"))
    # 6 duplicate pairs (12 results collapsing into 6 uniques)
    for i in range(6):
        results.append(make_result(f"Dup{i}", f"https://dup{i}.com/john/"))
        results.append(make_result(f"Dup{i}", f"https://www.dup{i}.com/john"))
    assert len(results) == 27
    deduped = deduplicate(results)
    assert len(deduped) == 21
