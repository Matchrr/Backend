from app.services.ai_client import parse_xano_user_id


def test_parse_xano_user_id_accepts_numeric_ids():
    assert parse_xano_user_id("42") == 42
    assert parse_xano_user_id(" 7 ") == 7


def test_parse_xano_user_id_rejects_demo_and_invalid():
    assert parse_xano_user_id("candidate_demo") is None
    assert parse_xano_user_id("0") is None
    assert parse_xano_user_id("") is None
    assert parse_xano_user_id(None) is None
