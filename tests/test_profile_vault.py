from app.schemas.candidate import Candidate, Experience
from app.services.grounding import CANDIDATE_ID
from app.services import profile_vault
from app.services.store import store


def _grounded_candidate(user_id: str = "42") -> Candidate:
    return Candidate(
        id=user_id,
        full_name="Ada Lovelace",
        email="ada@example.com",
        headline="Analyst",
        summary="Wrote the first algorithm.",
        target_title="Software Engineer",
        skills=["Python", "Mathematics"],
        experience=[
            Experience(title="Analyst", company="Babbage", bullets=["Designed the analytical engine notes"])
        ],
        grounded=True,
        grounding_sources=["resume"],
        linkedin_connected=True,
        linkedin_coverage="identity",
    )


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("MATCHR_PROFILE_DIR", str(tmp_path))
    candidate = _grounded_candidate()
    profile_vault.save(candidate, linkedin_tokens={"access_token": "tok"})

    loaded = profile_vault.load("42")
    assert loaded is not None
    assert loaded.candidate.full_name == "Ada Lovelace"
    assert loaded.candidate.grounded is True
    assert loaded.candidate.linkedin_connected is True
    assert loaded.linkedin_tokens == {"access_token": "tok"}


def test_demo_candidate_is_not_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("MATCHR_PROFILE_DIR", str(tmp_path))
    profile_vault.save(_grounded_candidate(CANDIDATE_ID))
    assert list(tmp_path.glob("*.json")) == []
    assert profile_vault.load(CANDIDATE_ID) is None


def test_empty_account_is_not_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("MATCHR_PROFILE_DIR", str(tmp_path))
    profile_vault.save(Candidate(id="99", email="new@example.com"))
    assert list(tmp_path.glob("*.json")) == []


def test_bind_identity_restores_saved_profile_after_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("MATCHR_PROFILE_DIR", str(tmp_path))
    store.reset()
    store.bind_identity("42", email="ada@example.com", full_name="Ada Lovelace")
    store.set_candidate(_grounded_candidate("wrong-id"))
    assert store.candidate.id == "42"
    assert (tmp_path / "42.json").is_file()

    store.reset()
    assert store.candidate.grounded is False
    restored = store.bind_identity("42", email="ada@example.com")
    assert restored.grounded is True
    assert restored.full_name == "Ada Lovelace"
    assert restored.linkedin_connected is True
    assert restored.skills == ["Python", "Mathematics"]


def test_reset_profile_deletes_saved_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("MATCHR_PROFILE_DIR", str(tmp_path))
    store.reset()
    store.bind_identity("7", email="ada@example.com")
    store.set_candidate(_grounded_candidate("7"))
    assert (tmp_path / "7.json").is_file()

    cleared = store.reset_profile()
    assert cleared.grounded is False
    assert cleared.id == "7"
    assert cleared.email == "ada@example.com"
    assert profile_vault.load("7") is None

    store.reset()
    again = store.bind_identity("7", email="ada@example.com")
    assert again.grounded is False
    assert again.experience == []


def test_switching_users_does_not_leak_profiles(tmp_path, monkeypatch):
    monkeypatch.setenv("MATCHR_PROFILE_DIR", str(tmp_path))
    store.reset()
    store.bind_identity("1", email="one@example.com")
    store.set_candidate(_grounded_candidate("1"))

    store.bind_identity("2", email="two@example.com", full_name="User Two")
    assert store.candidate.grounded is False
    assert store.candidate.full_name == "User Two"

    store.bind_identity("1")
    assert store.candidate.grounded is True
    assert store.candidate.full_name == "Ada Lovelace"
    assert store.candidate.email == "ada@example.com"
