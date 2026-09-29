from core.models import ResultStatus, SearchResult
from core.scorer import apply_scores, rank_results, score_result


def test_exact_username_high_priority_found():
    result = SearchResult(
        username="john",
        platform="Instagram",
        profile_url="https://instagram.com/john",
        status=ResultStatus.FOUND,
        source_engines=["maigret"],
    )
    score = score_result(result, "john")
    # found(40) + exact(30) + high_priority(10) = 80
    assert score == 80


def test_multi_engine_and_metadata_and_avatar_bonus():
    result = SearchResult(
        username="john",
        platform="Instagram",
        profile_url="https://instagram.com/john",
        status=ResultStatus.FOUND,
        source_engines=["maigret", "sherlock"],
        title="John Smith",
        avatar_url="https://instagram.com/john/avatar.jpg",
    )
    score = score_result(result, "john")
    # 40 + 30 + 10 (high) + 10 (multi-engine) + 5 (metadata) + 5 (avatar) = 100
    assert score == 100


def test_low_priority_platform_no_bonus():
    result = SearchResult(
        username="john",
        platform="SomeRandomForum",
        profile_url="https://forum.example.com/john",
        status=ResultStatus.FOUND,
        source_engines=["maigret"],
    )
    score = score_result(result, "john")
    # found(40) + exact(30) = 70, no high-priority bonus
    assert score == 70


def test_score_never_exceeds_100():
    result = SearchResult(
        username="john",
        platform="Instagram",
        profile_url="https://instagram.com/john",
        status=ResultStatus.FOUND,
        source_engines=["maigret", "sherlock", "custom"],
        title="x",
        description="y",
        avatar_url="z",
    )
    score = score_result(result, "john")
    assert score <= 100


def test_rank_results_instagram_before_low_priority_forum():
    high = SearchResult(
        username="john",
        platform="Instagram",
        profile_url="https://instagram.com/john",
        confidence=80,
    )
    low = SearchResult(
        username="john",
        platform="RandomForum",
        profile_url="https://forum.example.com/john",
        confidence=70,
    )
    ranked = rank_results([low, high])
    assert ranked[0].platform == "Instagram"
    assert ranked[1].platform == "RandomForum"


def test_apply_scores_sets_label():
    results = [
        SearchResult(
            username="john",
            platform="Instagram",
            profile_url="https://instagram.com/john",
            status=ResultStatus.FOUND,
            source_engines=["maigret"],
        )
    ]
    apply_scores(results, "john")
    assert results[0].confidence == 80
    assert results[0].confidence_label.value == "High"
