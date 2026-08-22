"""Builds the Ground Truth Profile from LinkedIn or an uploaded resume.

Nothing here infers experience the source document does not state. Skills are
resolved through the canonical taxonomy; bullets are carried over verbatim.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.candidate import Candidate, Experience
from app.services.matching import extract_skills

CANDIDATE_ID = "candidate_demo"

_SECTION_ALIASES = {
    "summary": {"summary", "profile", "objective", "about"},
    "experience": {"experience", "work experience", "employment", "professional experience"},
    "skills": {"skills", "technical skills", "core skills", "technologies"},
    "education": {"education", "academics"},
    "certifications": {"certifications", "certificates", "licenses"},
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
    experience = [
        Experience(
            title=role.get("title", ""),
            company=role.get("company", ""),
            start_date=role.get("start_date"),
            end_date=role.get("end_date"),
            bullets=list(role.get("bullets", [])),
        )
        for role in payload.get("experience", [])
    ]

    declared = list(payload.get("skills", []))
    inferred = extract_skills(
        " ".join(
            [payload.get("headline", ""), payload.get("summary", "")]
            + [bullet for role in experience for bullet in role.bullets]
        )
    )

    return Candidate(
        id=CANDIDATE_ID,
        full_name=payload.get("full_name"),
        headline=payload.get("headline"),
        summary=payload.get("summary"),
        location=payload.get("location"),
        target_title=target_title,
        skills=_merge_skills(declared, inferred),
        experience=experience,
        education=list(payload.get("education", [])),
        certifications=list(payload.get("certifications", [])),
        grounded=True,
        grounding_sources=["linkedin"],
        linkedin_connected=True,
    )


def ground_from_resume(text: str, target_title: str | None = None) -> Candidate:
    sections = _split_sections(text)
    experience = _parse_experience(sections.get("experience", []))
    declared = _parse_skills(sections.get("skills", []))
    inferred = extract_skills(text)

    return Candidate(
        id=CANDIDATE_ID,
        full_name=_guess_name(text),
        headline=_guess_headline(text),
        summary=" ".join(sections.get("summary", [])).strip() or None,
        location=_guess_location(text),
        target_title=target_title,
        skills=_merge_skills(declared, inferred),
        experience=experience,
        education=[line for line in sections.get("education", []) if line.strip()],
        certifications=[line for line in sections.get("certifications", []) if line.strip()],
        grounded=True,
        grounding_sources=["resume"],
    )


def merge_profiles(base: Candidate, incoming: Candidate) -> Candidate:
    """Layer a new source onto an existing profile without dropping facts."""
    merged = base.model_copy(deep=True)
    merged.full_name = incoming.full_name or merged.full_name
    merged.headline = incoming.headline or merged.headline
    merged.summary = incoming.summary or merged.summary
    merged.location = incoming.location or merged.location
    merged.target_title = merged.target_title or incoming.target_title
    merged.skills = _merge_skills(merged.skills, incoming.skills)
    merged.education = _dedupe(merged.education + incoming.education)
    merged.certifications = _dedupe(merged.certifications + incoming.certifications)

    known = {(role.title.lower(), role.company.lower()) for role in merged.experience}
    for role in incoming.experience:
        if (role.title.lower(), role.company.lower()) not in known:
            merged.experience.append(role)

    merged.grounded = True
    merged.grounding_sources = _dedupe(merged.grounding_sources + incoming.grounding_sources)
    merged.linkedin_connected = merged.linkedin_connected or incoming.linkedin_connected
    return merged


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
    match = re.search(r"^([A-Z][A-Za-z .]+,\s*[A-Z]{2})$", text, re.MULTILINE)
    return match.group(1).strip() if match else None
