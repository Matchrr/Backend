"""Durable Ground Truth Profile storage keyed by authenticated user id.

The in-memory Store is the working copy for a request. This module is what
survives process reloads and account switches so a grounded user does not have
to reconnect LinkedIn or re-upload a resume.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas.candidate import Candidate
from app.services.grounding import CANDIDATE_ID

logger = logging.getLogger(__name__)

_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass
class SavedProfile:
    candidate: Candidate
    linkedin_tokens: dict[str, object] | None = None
    profile_revision_id: int | None = None


def profile_dir() -> Path:
    override = (os.environ.get("MATCHR_PROFILE_DIR") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "data" / "profiles"


def is_persisted_user(user_id: str | None) -> bool:
    return bool(user_id) and user_id != CANDIDATE_ID


def worth_saving(candidate: Candidate) -> bool:
    return is_persisted_user(candidate.id) and bool(
        candidate.grounded
        or candidate.linkedin_connected
        or candidate.gmail_connected
        or candidate.target_title
        or candidate.headline
        or candidate.summary
        or candidate.skills
        or candidate.experience
        or candidate.education
        or candidate.picture_url
    )


def save(
    candidate: Candidate,
    *,
    linkedin_tokens: dict[str, object] | None = None,
    profile_revision_id: int | None = None,
) -> None:
    if not worth_saving(candidate):
        return
    path = _path_for(candidate.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidate": candidate.model_dump(),
        "linkedin_tokens": _tokens_payload(linkedin_tokens),
        "profile_revision_id": profile_revision_id,
    }
    encoded = json.dumps(payload, indent=2, ensure_ascii=False)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load(user_id: str) -> SavedProfile | None:
    if not is_persisted_user(user_id):
        return None
    path = _path_for(user_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read saved profile for user %s", user_id)
        return None
    if not isinstance(raw, dict):
        return None
    record = raw.get("candidate") if isinstance(raw.get("candidate"), dict) else raw
    try:
        candidate = Candidate.model_validate(record)
    except Exception:
        logger.exception("Saved profile for user %s is invalid", user_id)
        return None
    candidate.id = user_id
    tokens = raw.get("linkedin_tokens")
    revision = raw.get("profile_revision_id")
    try:
        revision_id = int(revision) if revision is not None else None
    except (TypeError, ValueError):
        revision_id = None
    return SavedProfile(
        candidate=candidate,
        linkedin_tokens=tokens if isinstance(tokens, dict) else None,
        profile_revision_id=revision_id,
    )


def delete(user_id: str) -> None:
    if not is_persisted_user(user_id):
        return
    path = _path_for(user_id)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not delete saved profile for user %s", user_id)


def _path_for(user_id: str) -> Path:
    cleaned = _SAFE_ID.sub("_", user_id.strip())[:120] or "unknown"
    return profile_dir() / f"{cleaned}.json"


def _tokens_payload(tokens: dict[str, object] | None) -> dict[str, Any] | None:
    if not tokens:
        return None
    payload = {
        key: tokens.get(key)
        for key in ("access_token", "refresh_token", "expires_in", "scope")
        if tokens.get(key) not in (None, "")
    }
    if not payload.get("access_token"):
        return None
    return payload
