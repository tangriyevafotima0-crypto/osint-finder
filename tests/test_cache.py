import time

import core.cache as cache_module
from core.models import SearchMode, SearchResult


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "search_cache_dir", lambda: tmp_path)
    results = [
        SearchResult(username="john", platform="Instagram", profile_url="https://instagram.com/john")
    ]
    cache_module.save("john", SearchMode.FAST, results)
    loaded = cache_module.load("john", SearchMode.FAST)
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].platform == "Instagram"


def test_cache_miss_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "search_cache_dir", lambda: tmp_path)
    assert cache_module.load("nonexistent", SearchMode.FAST) is None


def test_cache_expiration(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "search_cache_dir", lambda: tmp_path)
    path = cache_module._cache_path("john", SearchMode.FAST)
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    stale_payload = {
        "saved_at": time.time() - (cache_module.FAST_TTL_SECONDS + 10),
        "username": "john",
        "mode": "fast",
        "results": [],
    }
    path.write_text(json.dumps(stale_payload))
    assert cache_module.load("john", SearchMode.FAST) is None


def test_corrupted_cache_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "search_cache_dir", lambda: tmp_path)
    path = cache_module._cache_path("john", SearchMode.FAST)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not valid json ]")

    result = cache_module.load("john", SearchMode.FAST)
    assert result is None
    assert not path.exists()  # bad cache file removed


def test_incompatible_cache_schema_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "search_cache_dir", lambda: tmp_path)
    path = cache_module._cache_path("john", SearchMode.FAST)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"unexpected": "schema"}')

    result = cache_module.load("john", SearchMode.FAST)
    assert result is None
    assert not path.exists()


def test_deep_mode_uses_different_cache_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "search_cache_dir", lambda: tmp_path)
    fast_results = [SearchResult(username="john", platform="A", profile_url="https://a.com/john")]
    cache_module.save("john", SearchMode.FAST, fast_results)

    assert cache_module.load("john", SearchMode.DEEP) is None
    assert cache_module.load("john", SearchMode.FAST) is not None
