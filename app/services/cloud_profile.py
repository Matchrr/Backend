"""Profile persistence facade: Xano when configured, local JSON otherwise.

Real users stop writing `profile_vault` JSON once XANO_API_URL is set.
Tests and explicit disk mode keep the JSON vault as a double.
"""

from __future__ import annotations

import logging
import os

from app.core.config import settings
from app.schemas.candidate import Candidate
from app.services import profile_vault, s3_store, xano_profile
from app.services.profile_vault import SavedProfile

logger = logging.getLogger(__name__)


def use_xano() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    if (os.environ.get("MATCHR_PROFILE_DIR") or "").strip():
        return False
    if (os.environ.get("MATCHR_PROFILE_BACKEND") or "").strip().lower() == "disk":
        return False
    return bool(settings.xano_api_url)


def save(
    candidate: Candidate,
    *,
    linkedin_tokens: dict[str, object] | None = None,
    profile_revision_id: int | None = None,
    new_revision: bool = False,
) -> int | None:
    if not profile_vault.worth_saving(candidate):
        return profile_revision_id
    if use_xano():
        return xano_profile.save(candidate, new_revision=new_revision)
    profile_vault.save(
        candidate,
        linkedin_tokens=linkedin_tokens,
        profile_revision_id=profile_revision_id,
    )
    return profile_revision_id


def load(user_id: str) -> SavedProfile | None:
    if use_xano():
        return xano_profile.load(user_id)
    return profile_vault.load(user_id)


def delete(user_id: str) -> None:
    if use_xano():
        xano_profile.delete(user_id)
        try:
            s3_store.delete_user_prefix(user_id)
        except s3_store.S3StoreError:
            logger.exception("Could not delete S3 objects for user %s", user_id)
    profile_vault.delete(user_id)
