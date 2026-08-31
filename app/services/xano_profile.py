"""Ground Truth Profile persistence on Xano (`matchr_profile` + children)."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.schemas.candidate import Candidate, Experience
from app.services import profile_vault, xano_data
from app.services.ai_client import parse_xano_user_id

logger = logging.getLogger(__name__)

PROFILE = "matchr_profile"
EXPERIENCE = "matchr_experience"
EDUCATION = "matchr_education"
CERTIFICATION = "matchr_certification"
REVISION = "matchr_profile_revision"
SOURCE = "matchr_source_document"

KEEP_SOURCE_PER_KIND = 2


def save(candidate: Candidate, *, new_revision: bool = False) -> int | None:
    user_id = parse_xano_user_id(candidate.id)
    if user_id is None:
        return None
    row = _upsert_profile(user_id, candidate)
    profile_id = int(row["id"])
    _replace_children(user_id, profile_id, candidate)
    revision_id = _int(row.get("profile_revision_id"))
    if new_revision and candidate.grounded:
        revision = xano_data.add(
            REVISION,
            {
                "user_id": user_id,
                "accepted_at": _now_ms(),
                "sources": list(candidate.grounding_sources),
                "snapshot": candidate.model_dump(),
            },
        )
        revision_id = _int(revision.get("id"))
        xano_data.patch(
            PROFILE,
            profile_id,
            {"user_id": user_id, "profile_revision_id": revision_id, "updated_at": _now_ms()},
        )
    return revision_id


def load(user_id: str) -> profile_vault.SavedProfile | None:
    numeric = parse_xano_user_id(user_id)
    if numeric is None:
        return None
    row = _profile_row(numeric)
    if row is None:
        return None
    experiences = _rows_for_user(EXPERIENCE, numeric)
    education = _rows_for_user(EDUCATION, numeric)
    certs = _rows_for_user(CERTIFICATION, numeric)
    ordered = sorted(experiences, key=lambda item: _int(item.get("sort_order")) or 0)
    candidate = Candidate(
        id=user_id,
        full_name=_text(row.get("full_name")),
        headline=_text(row.get("headline")),
        summary=_text(row.get("summary")),
        email=_text(row.get("email")),
        picture_url=_text(row.get("picture_url")),
        websites=_string_list(row.get("websites")),
        skills=_string_list(row.get("skills")),
        languages=_string_list(row.get("languages")),
        honors=_string_list(row.get("honors")),
        projects=_string_list(row.get("projects")),
        target_title=_text(row.get("target_title")),
        location=_text(row.get("location")),
        grounded=bool(row.get("grounded")),
        grounding_sources=_string_list(row.get("grounding_sources")),
        linkedin_connected=bool(row.get("linkedin_connected")),
        linkedin_member_id=_text(row.get("linkedin_member_id")),
        linkedin_coverage=_text(row.get("linkedin_coverage")) or "none",
        gmail_connected=bool(row.get("gmail_connected")),
        experience=[
            _experience_from_row(item) for item in ordered if item.get("kind") != "volunteer"
        ],
        volunteering=[
            _experience_from_row(item) for item in ordered if item.get("kind") == "volunteer"
        ],
        education=_ordered_text(education, "school_text"),
        certifications=_ordered_text(certs, "cert_text"),
    )
    return profile_vault.SavedProfile(
        candidate=candidate,
        linkedin_tokens=None,
        profile_revision_id=_int(row.get("profile_revision_id")) or None,
    )


def delete(user_id: str) -> None:
    numeric = parse_xano_user_id(user_id)
    if numeric is None:
        return
    for table in (EXPERIENCE, EDUCATION, CERTIFICATION, REVISION, SOURCE, PROFILE):
        for row in _rows_for_user(table, numeric):
            record_id = row.get("id")
            if record_id is not None:
                xano_data.delete(table, record_id)


def record_source_document(
    *,
    user_id: int,
    kind: str,
    original_filename: str,
    content_type: str,
    byte_size: int,
    sha256: str,
    s3_key: str,
    nutrient_ok: bool,
    extracted_text_preview: str,
) -> dict[str, Any]:
    existing = _rows_for_user(SOURCE, user_id)
    same = next(
        (
            row
            for row in existing
            if row.get("sha256") == sha256 and row.get("kind") == kind and not _int(row.get("replaced_at"))
        ),
        None,
    )
    if same:
        return same
    now = _now_ms()
    current = [
        row
        for row in existing
        if row.get("kind") == kind and not _int(row.get("replaced_at"))
    ]
    if current:
        xano_data.patch(
            SOURCE,
            current[0]["id"],
            {"user_id": user_id, "replaced_at": now},
        )
        stale = [
            row
            for row in existing
            if row.get("kind") == kind and row["id"] != current[0]["id"]
        ]
        extra = stale[KEEP_SOURCE_PER_KIND - 1 :]
        for row in extra:
            xano_data.delete(SOURCE, row["id"])
    return xano_data.add(
        SOURCE,
        {
            "user_id": user_id,
            "kind": kind,
            "original_filename": original_filename,
            "content_type": content_type or "application/pdf",
            "byte_size": byte_size,
            "sha256": sha256,
            "s3_key": s3_key,
            "nutrient_ok": nutrient_ok,
            "extracted_text_preview": extracted_text_preview[:2000],
        },
    )


def _upsert_profile(user_id: int, candidate: Candidate) -> dict[str, Any]:
    existing = _profile_row(user_id)
    payload = {
        "user_id": user_id,
        "full_name": candidate.full_name or "",
        "headline": candidate.headline or "",
        "summary": candidate.summary or "",
        "email": candidate.email or "",
        "picture_url": candidate.picture_url or "",
        "websites": list(candidate.websites),
        "skills": list(candidate.skills),
        "languages": list(candidate.languages),
        "honors": list(candidate.honors),
        "projects": list(candidate.projects),
        "target_title": candidate.target_title or "",
        "location": candidate.location or "",
        "grounded": candidate.grounded,
        "grounding_sources": list(candidate.grounding_sources),
        "linkedin_connected": candidate.linkedin_connected,
        "linkedin_member_id": candidate.linkedin_member_id or "",
        "linkedin_coverage": candidate.linkedin_coverage or "none",
        "gmail_connected": candidate.gmail_connected,
        "updated_at": _now_ms(),
    }
    if candidate.grounded:
        payload["facts_accepted_at"] = _int(existing.get("facts_accepted_at") if existing else None) or _now_ms()
    if existing:
        return xano_data.patch(PROFILE, existing["id"], payload)
    return xano_data.add(PROFILE, payload)


def _replace_children(user_id: int, profile_id: int, candidate: Candidate) -> None:
    for table in (EXPERIENCE, EDUCATION, CERTIFICATION):
        for row in _rows_for_user(table, user_id):
            xano_data.delete(table, row["id"])
    for index, role in enumerate(candidate.experience):
        xano_data.add(EXPERIENCE, _experience_payload(user_id, profile_id, role, "work", index))
    for index, role in enumerate(candidate.volunteering):
        xano_data.add(EXPERIENCE, _experience_payload(user_id, profile_id, role, "volunteer", index))
    for index, school in enumerate(candidate.education):
        xano_data.add(
            EDUCATION,
            {
                "user_id": user_id,
                "profile_id": profile_id,
                "school_text": school,
                "sort_order": index,
            },
        )
    for index, cert in enumerate(candidate.certifications):
        xano_data.add(
            CERTIFICATION,
            {
                "user_id": user_id,
                "profile_id": profile_id,
                "cert_text": cert,
                "sort_order": index,
            },
        )


def _experience_payload(
    user_id: int,
    profile_id: int,
    role: Experience,
    kind: str,
    sort_order: int,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "profile_id": profile_id,
        "kind": kind,
        "title": role.title,
        "company": role.company,
        "location": role.location or "",
        "start_date": role.start_date or "",
        "end_date": role.end_date or "",
        "bullets": list(role.bullets),
        "sort_order": sort_order,
    }


def _experience_from_row(row: dict[str, Any]) -> Experience:
    return Experience(
        title=_text(row.get("title")) or "",
        company=_text(row.get("company")) or "",
        location=_text(row.get("location")),
        start_date=_text(row.get("start_date")),
        end_date=_text(row.get("end_date")),
        bullets=_string_list(row.get("bullets")),
    )


def _profile_row(user_id: int) -> dict[str, Any] | None:
    for row in xano_data.list_records(PROFILE):
        if _int(row.get("user_id")) == user_id:
            return row
    return None


def _rows_for_user(table: str, user_id: int) -> list[dict[str, Any]]:
    return [row for row in xano_data.list_records(table) if _int(row.get("user_id")) == user_id]


def _ordered_text(rows: list[dict[str, Any]], field: str) -> list[str]:
    ordered = sorted(rows, key=lambda row: _int(row.get("sort_order")) or 0)
    return [text for text in (_text(row.get(field)) for row in ordered) if text]


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number else None


def _now_ms() -> int:
    return int(time.time() * 1000)
