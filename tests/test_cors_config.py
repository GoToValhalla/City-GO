from core.cors import parse_cors_origins


def test_parse_cors_origins_splits_comma_separated_values() -> None:
    assert parse_cors_origins("https://a.test, https://b.test") == [
        "https://a.test",
        "https://b.test",
    ]


def test_parse_cors_origins_falls_back_to_local_frontend() -> None:
    assert "http://localhost:5173" in parse_cors_origins("")
