from core.models import ConfidenceLabel, ResultStatus, SearchResult, confidence_label


def test_confidence_label_thresholds():
    assert confidence_label(100) == ConfidenceLabel.HIGH
    assert confidence_label(80) == ConfidenceLabel.HIGH
    assert confidence_label(79) == ConfidenceLabel.MEDIUM
    assert confidence_label(50) == ConfidenceLabel.MEDIUM
    assert confidence_label(49) == ConfidenceLabel.LOW
    assert confidence_label(0) == ConfidenceLabel.LOW


def test_search_result_json_roundtrip():
    result = SearchResult(
        username="john_smith",
        platform="Instagram",
        profile_url="https://instagram.com/john_smith",
        status=ResultStatus.FOUND,
        confidence=91,
        confidence_label=ConfidenceLabel.HIGH,
        source_engines=["maigret"],
    )
    data = result.to_json()
    restored = SearchResult.from_json(data)

    assert restored.username == result.username
    assert restored.platform == result.platform
    assert restored.profile_url == result.profile_url
    assert restored.confidence == 91
    assert restored.confidence_label == ConfidenceLabel.HIGH
    assert restored.source_engines == ["maigret"]


def test_search_result_no_raw_html_field():
    result = SearchResult(username="x", platform="Y", profile_url="https://y.com/x")
    assert not hasattr(result, "raw_html")
    assert not hasattr(result, "cookies")
