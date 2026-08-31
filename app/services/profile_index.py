"""Best-effort sync of the grounded profile into Xano `matchrr_profile_chunk`."""

from __future__ import annotations

import logging

from app.schemas.candidate import Candidate
from app.services import ai_client
from app.services.store import store

logger = logging.getLogger(__name__)


def commit_grounded(candidate: Candidate) -> Candidate:
    stored = store.set_candidate(candidate)
    sync_profile_chunks(stored)
    return stored


def sync_profile_chunks(candidate: Candidate) -> None:
    if not candidate.grounded or not ai_client.ai_service_reachable():
        return
    user_id = ai_client.parse_xano_user_id(candidate.id)
    if user_id is None:
        return
    try:
        ai_client.sync_profile_chunks(
            {
                "user_id": user_id,
                "profile_revision_id": store.profile_revision_id(),
                "profile": store.profile_payload(),
            }
        )
    except Exception:
        logger.exception("Profile chunk sync failed for user %s", user_id)
