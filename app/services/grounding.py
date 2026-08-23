"""Builds the Ground Truth Profile from LinkedIn or an uploaded resume.

Nothing here infers experience the source document does not state. Skills are
resolved through the canonical taxonomy; bullets are carried over verbatim.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.candidate import Candidate, Experience
from app.services.career_parse import (
    city_only_location,
    education_from_plaintext,
    normalize_education,
    normalize_payload,
    normalize_roles,
    normalize_skills,
    roles_from_plaintext,
    roles_from_resume_lines,
)
from app.services.matching import extract_skills

CANDIDATE_ID = "candidate_demo"

_SECTION_ALIASES = {
    "summary": {"summary", "profile", "objective", "about"},
    "experience": {
        "experience",
        "work experience",
        "employment",
        "professional experience",
        "relevant experience",
        "work history",
        "employment history",
    },
    "skills": {"skills", "technical skills", "core skills", "technologies"},
    "education": {"education", "academics"},
    "certifications": {"certifications", "certificates", "licenses"},
    "volunteering": {"volunteering", "volunteer", "volunteer experience", "volunteering experience"},
    "projects": {"projects", "selected projects"},
}

_BULLET_PREFIX = re.compile(r"^\s*[-•*\u2022]\s+")
_DATE_RANGE = re.compile(r"\(?\s*(\d{4})\s*[–\-—to]+\s*(\d{4}|present|current)\s*\)?", re.I)


def extract_pdf_text(payload: bytes) -> str:
    """Extract text from an uploaded resume.

    Uses pypdf when the upload is a real PDF; plain text uploads pass through so
    the flow is testable without a PDF handy. Swapping in the Nutrient/Foxit
    Document API later means replacing only this function.
    """
    if payload[:5] != b"%PDF-":
        return payload.decode("utf-8", errors="ignore")

    try:
        from io import BytesIO

        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(BytesIO(payload))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def ground_from_linkedin(payload: dict[str, Any], target_title: str | None = None) -> Candidate:
    experience = [_coerce_experience(role) for role in payload.get("experience", [])]
    experience = [role for role in experience if role.title or role.company]
    volunteering = [_coerce_experience(role) for role in payload.get("volunteering", [])]
    volunteering = [role for role in volunteering if role.title or role.company]

    declared = list(payload.get("skills", []))
    inferred = extract_skills(
        " ".join(
            [payload.get("headline") or "", payload.get("summary") or ""]
            + [bullet for role in experience for bullet in role.bullets]
            + [bullet for role in volunteering for bullet in role.bullets]
            + list(payload.get("projects", []))
        )
    )
    skills = _merge_skills(declared, inferred)
    education = [line for line in payload.get("education", []) if str(line).strip()]
    certifications = [line for line in payload.get("certifications", []) if str(line).strip()]
    projects = [line for line in payload.get("projects", []) if str(line).strip()]
    languages = [line for line in payload.get("languages", []) if str(line).strip()]
    honors = [line for line in payload.get("honors", []) if str(line).strip()]
    websites = [line for line in payload.get("websites", []) if str(line).strip()]

    has_career_facts = bool(
        experience or skills or education or payload.get("summary") or payload.get("headline")
    )

    return _candidate_from_payload(
        payload,
        skills=skills,
        experience=experience,
        education=education,
        certifications=certifications,
        volunteering=volunteering,
        projects=projects,
        languages=languages,
        honors=honors,
        websites=websites,
        target_title=target_title,
        grounded=has_career_facts,
        source="linkedin",
        linkedin_connected=True,
        linkedin_coverage="profile" if has_career_facts else "identity",
    )


def ground_from_extracted(
    payload: dict[str, Any],
    target_title: str | None = None,
    source: str = "resume",
) -> Candidate:
    """Map Nutrient (or any structured extractor) output into the Candidate card."""
    payload = normalize_payload(payload) or payload
    experience = [_coerce_experience(role) for role in payload.get("experience", [])]
    experience = [role for role in experience if role.title or role.company]
    volunteering = [_coerce_experience(role) for role in payload.get("volunteering", [])]
    volunteering = [role for role in volunteering if role.title or role.company]
    skills = _merge_skills(
        list(payload.get("skills") or []),
        extract_skills(
            " ".join(
                [payload.get("headline") or "", payload.get("summary") or ""]
                + [bullet for role in experience for bullet in role.bullets]
                + [bullet for role in volunteering for bullet in role.bullets]
                + [str(item) for item in payload.get("projects", []) or []]
            )
        ),
    )
    education = list(payload.get("education") or [])
    return _candidate_from_payload(
        payload,
        skills=skills,
        experience=experience,
        education=education,
        certifications=[str(line).strip() for line in payload.get("certifications", []) or [] if str(line).strip()],
        volunteering=volunteering,
        projects=[str(line).strip() for line in payload.get("projects", []) or [] if str(line).strip()],
        languages=[str(line).strip() for line in payload.get("languages", []) or [] if str(line).strip()],
        honors=[str(line).strip() for line in payload.get("honors", []) or [] if str(line).strip()],
        websites=[str(line).strip() for line in payload.get("websites", []) or [] if str(line).strip()],
        target_title=target_title,
        grounded=bool(experience or skills or education or payload.get("summary") or payload.get("headline")),
        source=source,
        linkedin_connected=False,
        linkedin_coverage="none",
    )


def _candidate_from_payload(
    payload: dict[str, Any],
    *,
    skills: list[str],
    experience: list[Experience],
    education: list[str],
    certifications: list[str],
    volunteering: list[Experience],
    projects: list[str],
    languages: list[str],
    honors: list[str],
    websites: list[str],
    target_title: str | None,
    grounded: bool,
    source: str,
    linkedin_connected: bool,
    linkedin_coverage: str,
) -> Candidate:
    return Candidate(
        id=CANDIDATE_ID,
        full_name=payload.get("full_name") or None,
        headline=payload.get("headline") or None,
        summary=payload.get("summary") or None,
        location=city_only_location(payload.get("location")),
        email=payload.get("email") or None,
        picture_url=payload.get("picture") or payload.get("picture_url"),
        websites=websites,
        target_title=target_title,
        skills=skills,
        experience=experience,
        education=education,
        certifications=certifications,
        volunteering=volunteering,
        projects=projects,
        languages=languages,
        honors=honors,
        grounded=grounded,
        grounding_sources=[source] if grounded else [],
        linkedin_connected=linkedin_connected,
        linkedin_member_id=payload.get("linkedin_member_id"),
        linkedin_coverage=linkedin_coverage,
    )


def _coerce_experience(role: dict[str, Any] | Experience) -> Experience:
    if isinstance(role, Experience):
        return role
    if isinstance(role, str):
        parsed = normalize_roles([role])
        role = parsed[0] if parsed else {"title": "", "company": role}
    bullets = [str(item).strip() for item in (role.get("bullets") or []) if str(item).strip()]
    if not bullets and role.get("description"):
        bullets = [line.strip() for line in str(role["description"]).splitlines() if line.strip()]
    return Experience(
        title=role.get("title") or "",
        company=role.get("company") or "",
        start_date=role.get("start_date") or None,
        end_date=role.get("end_date") or None,
        location=role.get("location") or None,
        bullets=bullets,
    )


def ground_from_resume(text: str, target_title: str | None = None) -> Candidate:
    sections = _split_sections(text)
    experience_lines = sections.get("experience") or []
    volunteering_lines = sections.get("volunteering") or []
    parsed_roles = roles_from_resume_lines(experience_lines) or roles_from_plaintext(text)
    experience = [_coerce_experience(role) for role in parsed_roles]
    volunteering = [_coerce_experience(role) for role in roles_from_resume_lines(volunteering_lines)]
    declared = normalize_skills(sections.get("skills", []))
    education = normalize_education(sections.get("education", [])) or education_from_plaintext(text)

    return Candidate(
        id=CANDIDATE_ID,
        full_name=_guess_name(text),
        headline=_guess_headline(text),
        summary=" ".join(sections.get("summary", [])).strip() or None,
        location=city_only_location(_guess_location(text)),
        target_title=target_title,
        skills=_merge_skills(declared, extract_skills(text)),
        experience=experience,
        education=education,
        certifications=[line for line in sections.get("certifications", []) if line.strip()],
        volunteering=volunteering,
        projects=[line for line in sections.get("projects", []) if line.strip()],
        grounded=True,
        grounding_sources=["resume"],
    )


def overlay_document(base: Candidate, incoming: Candidate) -> Candidate:
    """Keep LinkedIn identity; the uploaded document owns career rows."""
    merged = merge_profiles(base, incoming)
    merged.full_name = base.full_name or incoming.full_name
    merged.email = base.email or incoming.email
    merged.picture_url = base.picture_url or incoming.picture_url
    if incoming.experience:
        merged.experience = incoming.experience
    if incoming.education:
        merged.education = incoming.education
    if incoming.volunteering:
        merged.volunteering = incoming.volunteering
    if incoming.skills:
        merged.skills = incoming.skills
    if incoming.projects:
        merged.projects = incoming.projects
    if incoming.certifications:
        merged.certifications = incoming.certifications
    if incoming.summary:
        merged.summary = incoming.summary
    if incoming.headline and not base.headline:
        merged.headline = incoming.headline
    return merged


def merge_profiles(base: Candidate, incoming: Candidate) -> Candidate:
    """Layer a new source onto an existing profile without dropping facts."""
    merged = base.model_copy(deep=True)
    merged.full_name = incoming.full_name or merged.full_name
    merged.headline = incoming.headline or merged.headline
    merged.summary = incoming.summary or merged.summary
    merged.location = city_only_location(incoming.location) or city_only_location(merged.location)
    merged.email = incoming.email or merged.email
    merged.picture_url = incoming.picture_url or merged.picture_url
    merged.target_title = merged.target_title or incoming.target_title
    merged.skills = _merge_skills(merged.skills, incoming.skills)
    merged.education = _dedupe(merged.education + incoming.education)
    merged.certifications = _dedupe(merged.certifications + incoming.certifications)
    merged.projects = _dedupe(merged.projects + incoming.projects)
    merged.languages = _dedupe(merged.languages + incoming.languages)
    merged.honors = _dedupe(merged.honors + incoming.honors)
    merged.websites = _dedupe(merged.websites + incoming.websites)

    _append_roles(merged.experience, incoming.experience)
    _append_roles(merged.volunteering, incoming.volunteering)

    merged.grounded = merged.grounded or incoming.grounded
    merged.grounding_sources = _dedupe(merged.grounding_sources + incoming.grounding_sources)
    merged.linkedin_connected = merged.linkedin_connected or incoming.linkedin_connected
    merged.linkedin_member_id = incoming.linkedin_member_id or merged.linkedin_member_id
    merged.linkedin_coverage = _richer_coverage(merged.linkedin_coverage, incoming.linkedin_coverage)
    return merged


def _append_roles(existing: list[Experience], incoming: list[Experience]) -> None:
    known = {(role.title.lower(), role.company.lower()) for role in existing}
    for role in incoming:
        if (role.title.lower(), role.company.lower()) not in known:
            existing.append(role)


def _richer_coverage(left: str, right: str) -> str:
    rank = {"none": 0, "identity": 1, "profile": 2}
    return left if rank.get(left, 0) >= rank.get(right, 0) else right


def _merge_skills(*groups: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for group in groups:
        for skill in group:
            key = skill.strip().lower()
            if key and key not in seen:
                seen[key] = skill.strip()
    return list(seen.values())


def _dedupe(values: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen[key] = value.strip()
    return list(seen.values())


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading = _match_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        if current and line.strip():
            sections[current].append(line)
    return sections


def _match_heading(line: str) -> str | None:
    stripped = line.strip().rstrip(":").lower()
    if not stripped or len(stripped) > 40:
        return None
    for section, aliases in _SECTION_ALIASES.items():
        if stripped in aliases:
            return section
    return None


def _parse_experience(lines: list[str]) -> list[Experience]:
    roles: list[Experience] = []
    current: Experience | None = None

    for line in lines:
        if _BULLET_PREFIX.match(line):
            if current is not None:
                current.bullets.append(_BULLET_PREFIX.sub("", line).strip())
            continue

        header = line.strip()
        if not header:
            continue
        if current is not None:
            roles.append(current)

        start = end = None
        date_match = _DATE_RANGE.search(header)
        if date_match:
            start, end = date_match.group(1), date_match.group(2)
            header = _DATE_RANGE.sub("", header).strip()

        company, title = _split_company_title(header)
        current = Experience(title=title, company=company, start_date=start, end_date=end)

    if current is not None:
        roles.append(current)
    return roles


def _split_company_title(header: str) -> tuple[str, str]:
    for separator in ("—", "–", " - ", "|", ","):
        if separator in header:
            left, _, right = header.partition(separator)
            return left.strip(), right.strip()
    return header.strip(), ""


def _parse_skills(lines: list[str]) -> list[str]:
    tokens: list[str] = []
    for line in lines:
        cleaned = _BULLET_PREFIX.sub("", line)
        tokens.extend(part.strip() for part in re.split(r"[,;|]", cleaned))
    return [token for token in tokens if token and len(token) < 40]


def _guess_name(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        head = re.split(r"[—–|]", stripped)[0].strip()
        words = head.split()
        if 1 < len(words) <= 4 and all(word[:1].isupper() for word in words if word):
            return head
        return None
    return None


def _guess_headline(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if "—" in stripped or "–" in stripped:
            parts = re.split(r"[—–]", stripped, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()
    return None


def _guess_location(text: str) -> str | None:
    for match in re.finditer(r"^([A-Z][A-Za-z .]+,\s*[A-Z]{2})$", text, re.MULTILINE):
        city = city_only_location(match.group(1).strip())
        if city:
            return city
    return None
