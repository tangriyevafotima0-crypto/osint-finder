import pytest

import core.cache as cache_module
from core.models import SearchMode, SearchResult, SearchState
from core.search_manager import SearchManager


def make_result(platform, url, username="john"):
    return SearchResult(username=username, platform=platform, profile_url=url, source_engines=["maigret"])


@pytest.fixture(autouse=True)
def isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "search_cache_dir", lambda: tmp_path)


@pytest.mark.asyncio
async def test_enrichment_budget_caps_at_max_enrich(monkeypatch):
    # 27 discovered candidates across distinct platforms/urls -> no dedup collapse
    results = [make_result(f"Site{i}", f"https://site{i}.com/john") for i in range(27)]

    async def fake_engine_search(self, username, mode):
        return results

    enrich_calls = []

    async def fake_enrich_profile(result):
        enrich_calls.append(result.profile_url)
        result.enriched = True
        return result

    monkeypatch.setattr("core.search_manager.MaigretEngine.search", fake_engine_search)
    monkeypatch.setattr("core.search_manager.enrich_profile", fake_enrich_profile)

    manager = SearchManager(max_enrich=8)
    response = await manager.search("john", mode=SearchMode.FAST)

    assert response.state == SearchState.SUCCESS
    assert response.metrics.results_found == 27
    assert response.metrics.results_unique == 27
    assert len(enrich_calls) == 8
    assert response.metrics.results_enriched == 8


@pytest.mark.asyncio
async def test_instagram_enriched_before_low_priority_forum(monkeypatch):
    results = [make_result(f"Forum{i}", f"https://forum{i}.com/john") for i in range(10)]
    results.append(make_result("Instagram", "https://instagram.com/john"))

    async def fake_engine_search(self, username, mode):
        return results

    enriched_order = []

    async def fake_enrich_instagram(result):
        enriched_order.append(result.platform)
        result.enriched = True
        return result

    async def fake_enrich_profile(result):
        enriched_order.append(result.platform)
        result.enriched = True
        return result

    monkeypatch.setattr("core.search_manager.MaigretEngine.search", fake_engine_search)
    monkeypatch.setattr("core.search_manager.enrich_instagram", fake_enrich_instagram)
    monkeypatch.setattr("core.search_manager.enrich_profile", fake_enrich_profile)

    manager = SearchManager(max_enrich=3)
    response = await manager.search("john", mode=SearchMode.FAST)

    assert response.state == SearchState.SUCCESS
    assert enriched_order[0] == "Instagram"


@pytest.mark.asyncio
async def test_no_results_state(monkeypatch):
    async def fake_engine_search(self, username, mode):
        return []

    monkeypatch.setattr("core.search_manager.MaigretEngine.search", fake_engine_search)

    manager = SearchManager()
    response = await manager.search("nobodyhasthisname", mode=SearchMode.FAST)
    assert response.state == SearchState.NO_RESULTS


@pytest.mark.asyncio
async def test_invalid_username_returns_error(monkeypatch):
    manager = SearchManager()
    response = await manager.search("invalid username with spaces!!", mode=SearchMode.FAST)
    assert response.state == SearchState.ERROR


@pytest.mark.asyncio
async def test_engine_exception_does_not_crash_search(monkeypatch):
    async def broken_search(self, username, mode):
        raise RuntimeError("network exploded")

    monkeypatch.setattr("core.search_manager.MaigretEngine.search", broken_search)

    manager = SearchManager()
    response = await manager.search("john", mode=SearchMode.FAST)
    assert response.state == SearchState.ERROR
    assert response.results == []


@pytest.mark.asyncio
async def test_cache_hit_skips_discovery(monkeypatch):
    call_count = {"n": 0}

    async def fake_engine_search(self, username, mode):
        call_count["n"] += 1
        return [make_result("GitHub", "https://github.com/john")]

    monkeypatch.setattr("core.search_manager.MaigretEngine.search", fake_engine_search)
    monkeypatch.setattr("core.search_manager.enrich_profile", lambda r: r)

    manager = SearchManager()
    await manager.search("john", mode=SearchMode.FAST)
    assert call_count["n"] == 1

    # Second call should hit cache, not call engine again
    response2 = await manager.search("john", mode=SearchMode.FAST)
    assert call_count["n"] == 1
    assert response2.metrics.cache_hit is True


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache(monkeypatch):
    call_count = {"n": 0}

    async def fake_engine_search(self, username, mode):
        call_count["n"] += 1
        return [make_result("GitHub", "https://github.com/john")]

    async def fake_enrich_profile(result):
        result.enriched = True
        return result

    monkeypatch.setattr("core.search_manager.MaigretEngine.search", fake_engine_search)
    monkeypatch.setattr("core.search_manager.enrich_profile", fake_enrich_profile)

    manager = SearchManager()
    await manager.search("john", mode=SearchMode.FAST)
    await manager.search("john", mode=SearchMode.FAST, force_refresh=True)
    assert call_count["n"] == 2
