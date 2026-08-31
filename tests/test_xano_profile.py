from app.schemas.candidate import Candidate, Experience
from app.services import xano_data, xano_profile


class MemoryXano:
    def __init__(self) -> None:
        self.tables: dict[str, dict[int, dict]] = {}
        self._seq = 0

    def list_records(self, table: str, params=None):
        return list(self.tables.get(table, {}).values())

    def add(self, table: str, payload: dict) -> dict:
        self._seq += 1
        row = {"id": self._seq, **payload}
        self.tables.setdefault(table, {})[self._seq] = row
        return row

    def patch(self, table: str, record_id, payload: dict) -> dict:
        row = self.tables[table][int(record_id)]
        row.update(payload)
        return row

    def delete(self, table: str, record_id) -> None:
        self.tables.get(table, {}).pop(int(record_id), None)


def _candidate() -> Candidate:
    return Candidate(
        id="42",
        full_name="Ada Lovelace",
        email="ada@example.com",
        headline="Analyst",
        target_title="Software Engineer",
        location="London",
        skills=["Python"],
        experience=[Experience(title="Analyst", company="Babbage", bullets=["Notes"])],
        education=["University of London"],
        certifications=["None"],
        grounded=True,
        grounding_sources=["resume"],
    )


def test_save_and_load_profile_round_trip(monkeypatch):
    mem = MemoryXano()
    monkeypatch.setattr(xano_data, "list_records", mem.list_records)
    monkeypatch.setattr(xano_data, "add", mem.add)
    monkeypatch.setattr(xano_data, "patch", mem.patch)
    monkeypatch.setattr(xano_data, "delete", mem.delete)

    revision_id = xano_profile.save(_candidate(), new_revision=True)
    assert revision_id is not None

    loaded = xano_profile.load("42")
    assert loaded is not None
    assert loaded.candidate.full_name == "Ada Lovelace"
    assert loaded.candidate.grounded is True
    assert loaded.candidate.experience[0].company == "Babbage"
    assert loaded.candidate.education == ["University of London"]
    assert loaded.profile_revision_id == revision_id


def test_record_source_document_dedups_same_hash(monkeypatch):
    mem = MemoryXano()
    monkeypatch.setattr(xano_data, "list_records", mem.list_records)
    monkeypatch.setattr(xano_data, "add", mem.add)
    monkeypatch.setattr(xano_data, "patch", mem.patch)
    monkeypatch.setattr(xano_data, "delete", mem.delete)

    kwargs = dict(
        user_id=42,
        kind="resume",
        original_filename="cv.pdf",
        content_type="application/pdf",
        byte_size=12,
        sha256="abc",
        s3_key="users/42/sources/abc.pdf",
        nutrient_ok=True,
        extracted_text_preview="Ada",
    )
    first = xano_profile.record_source_document(**kwargs)
    second = xano_profile.record_source_document(**kwargs)
    assert first["id"] == second["id"]
    assert len(mem.tables["matchr_source_document"]) == 1


def test_cloud_profile_stays_on_disk_during_pytest(tmp_path, monkeypatch):
    from app.services import cloud_profile

    monkeypatch.setenv("MATCHR_PROFILE_DIR", str(tmp_path))
    assert cloud_profile.use_xano() is False
