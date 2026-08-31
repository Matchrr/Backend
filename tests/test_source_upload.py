import hashlib

from app.api.routes.candidates import _normalize_kind, _store_source_pdf
from app.services import s3_store, xano_profile
from app.services.store import store


def test_normalize_kind_maps_wizard_values():
    assert _normalize_kind("linkedin-pdf") == "linkedin_pdf"
    assert _normalize_kind("linkedin_pdf") == "linkedin_pdf"
    assert _normalize_kind("resume") == "resume"
    assert _normalize_kind("") == "resume"


def test_store_source_pdf_uploads_and_records(monkeypatch):
    store.reset()
    store.candidate.id = "42"
    captured: dict = {}

    monkeypatch.setattr(s3_store, "configured", lambda: True)
    monkeypatch.setattr(
        s3_store,
        "put_source_pdf",
        lambda **kwargs: captured.update(kwargs) or s3_store.source_key(kwargs["user_id"], kwargs["sha256"]),
    )

    recorded: dict = {}

    def fake_record(**kwargs):
        recorded.update(kwargs)
        return {"id": 1, **kwargs}

    monkeypatch.setattr(xano_profile, "record_source_document", fake_record)

    body = b"%PDF-1.4 hello"
    _store_source_pdf(
        body,
        filename="resume.pdf",
        content_type="application/pdf",
        kind="resume",
        nutrient_ok=True,
        preview="hello",
    )
    assert captured["user_id"] == 42
    assert captured["sha256"] == hashlib.sha256(body).hexdigest()
    assert recorded["s3_key"] == "users/42/sources/" + captured["sha256"] + ".pdf"
    assert recorded["kind"] == "resume"


def test_store_source_pdf_skips_non_pdf(monkeypatch):
    called = False

    def boom(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(s3_store, "configured", lambda: True)
    monkeypatch.setattr(s3_store, "put_source_pdf", boom)
    _store_source_pdf(
        b"not a pdf",
        filename="notes.txt",
        content_type="text/plain",
        kind="resume",
        nutrient_ok=False,
        preview="",
    )
    assert called is False
