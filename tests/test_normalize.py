from core.normalize import (
    is_valid_username,
    normalize_platform_name,
    normalize_profile_url,
    normalize_username,
)


def test_strip_at_symbol():
    assert normalize_username("@john_smith") == "john_smith"


def test_strip_whitespace():
    assert normalize_username("  john_smith  ") == "john_smith"


def test_instagram_url_to_username():
    assert normalize_username("https://instagram.com/john_smith") == "john_smith"
    assert normalize_username("https://www.instagram.com/john_smith/") == "john_smith"


def test_github_url_to_username():
    assert normalize_username("https://github.com/octocat") == "octocat"


def test_plain_username_unchanged():
    assert normalize_username("john_smith") == "john_smith"


def test_empty_input():
    assert normalize_username("") == ""
    assert normalize_username(None) == ""


def test_valid_username():
    assert is_valid_username("john_smith")
    assert not is_valid_username("")
    assert not is_valid_username("john smith")  # space not allowed
    assert not is_valid_username("a" * 101)


def test_profile_url_dedup_equivalence():
    a = normalize_profile_url("https://instagram.com/john")
    b = normalize_profile_url("https://www.instagram.com/john/")
    assert a == b


def test_platform_name_alias():
    assert normalize_platform_name("x.com") == "X"
    assert normalize_platform_name("GitHub") == "GitHub"
