from stock_research.auth import security


def test_hash_and_verify_password() -> None:
    password_hash = security.hash_password("correct-horse-battery")
    assert security.verify_password(password_hash, "correct-horse-battery")
    assert not security.verify_password(password_hash, "wrong-password")


def test_access_token_roundtrip() -> None:
    token = security.create_access_token(
        sub="user-123",
        tenant="tenant-123",
        scopes=["self"],
    )
    payload = security.decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["tenant"] == "tenant-123"
    assert payload["scopes"] == ["self"]
    assert payload["iss"] == "stock-research"
    assert payload["aud"] == "stock-research-web"


def test_refresh_token_hash_is_deterministic_and_hashed() -> None:
    refresh_token = security.generate_refresh_token()
    assert refresh_token != security.hash_refresh_token(refresh_token)
    assert security.hash_refresh_token(refresh_token) == security.hash_refresh_token(refresh_token)
