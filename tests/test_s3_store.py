from app.services.s3_store import source_key, user_prefix


def test_source_key_layout():
    assert source_key(42, "abc123") == "users/42/sources/abc123.pdf"


def test_user_prefix_for_wipe():
    assert user_prefix("42") == "users/42/"


def test_put_source_pdf_sets_metadata_and_sse(monkeypatch):
    from app.core import config
    from app.services import s3_store

    captured: dict = {}

    class FakeClient:
        def put_object(self, **kwargs):
            captured.update(kwargs)
            return {}

    monkeypatch.setattr(config.settings, "matchr_s3_bucket", "matchr-dev")
    monkeypatch.setattr(config.settings, "aws_access_key_id", "AKIATEST")
    monkeypatch.setattr(s3_store, "_client", lambda: FakeClient())

    key = s3_store.put_source_pdf(
        user_id=7,
        sha256="deadbeef",
        body=b"%PDF-1.4 test",
        kind="resume",
    )
    assert key == "users/7/sources/deadbeef.pdf"
    assert captured["Bucket"] == "matchr-dev"
    assert captured["ContentType"] == "application/pdf"
    assert captured["ServerSideEncryption"] == "AES256"
    assert captured["Metadata"]["user-id"] == "7"
    assert captured["Metadata"]["kind"] == "source_resume"
