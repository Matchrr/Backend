"""Normalize career facts from Nutrient JSON or LinkedIn PDF OCR.

LinkedIn Save-to-PDF often flattens a role into middot-separated text:
title, company, dates, city, then a description. Naive parsers treat every
fragment as a new job. This module maps those blobs onto one role per job
and one line per school.
"""

from __future__ import annotations

import re
from typing import Any

_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_DATE_ATOM = rf"(?:{_MONTH}\.?\s+\d{{4}}|\d{{1,2}}/\d{{4}}|(?:19|20)\d{{2}})"
_DATE_END = rf"(?:{_DATE_ATOM}|Present|Current|Now)"
_DATE_SEP = r"(?:\s*[-–—]\s*|\s+to\s+)"
_DATE_SPAN = re.compile(
    rf"({_DATE_ATOM}{_DATE_SEP}{_DATE_END})"
    rf"(?:\s*\(\s*\d+\s*(?:mos?|months?|yrs?|years?)\s*\))?",
    re.I,
)
_DURATION = re.compile(r"\(\s*\d+\s*(?:mos?|months?|yrs?|years?)\s*\)", re.I)
_BULLET_PREFIX = re.compile(r"^\s*[-•*\u2022–—]\s+")
_MIDDOT_SPLIT = re.compile(r"\s*[·•|]\s*|\s+[—–]\s+")
_HEADING_PREFIX = re.compile(
    r"^(top\s+skills|skills|experience|education|summary|profile|about|"
    r"volunteering|projects|certifications|licenses|honors|languages|"
    r"contact|featured)\s*[:·•|\-]?\s*",
    re.I,
)
_HEADINGS = {
    "experience",
    "education",
    "skills",
    "top skills",
    "summary",
    "profile",
    "about",
    "volunteering",
    "volunteer experience",
    "projects",
    "certifications",
    "licenses",
    "licenses & certifications",
    "honors",
    "honors & awards",
    "languages",
    "contact",
    "featured",
    "activity",
    "publications",
}
_TITLE_HINTS = (
    "engineer",
    "developer",
    "intern",
    "manager",
    "analyst",
    "scientist",
    "designer",
    "founder",
    "consultant",
    "director",
    "architect",
    "specialist",
    "researcher",
    "associate",
    "fellow",
    "programmer",
    "officer",
    "coordinator",
    "assistant",
    "president",
    "co-founder",
    "cofounder",
)
_PROSE_STOPWORDS = {
    "the",
    "a",
    "an",
    "to",
    "of",
    "and",
    "that",
    "how",
    "with",
    "for",
    "in",
    "inside",
    "aimed",
    "can",
    "help",
    "how",
    "children",
    "improving",
}
_PDF_JUNK = re.compile(r"\bpage\s+\d+\s+(?:of|\/)\s*\d+\b", re.I)
_INSTITUTION = re.compile(
    r"(?:[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,5}\s+)?"
    r"(?:University|College|Institute|Academy|Polytechnic)\b"
    r"(?:\s+of(?:\s+[A-Z][\w'.-]+){1,4})?"
    r"|(?:[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,4}\s+School)\b"
)
_SCHOOL_HINT = re.compile(
    r"\b(university|college|institute|school|academy|polytechnic)\b",
    re.I,
)
_DEGREE_HINT = re.compile(
    r"\b(bachelor|master|phd|doctor|diploma|associate|b\.?s\.?|m\.?s\.?|b\.?a\.?|"
    r"m\.?a\.?|mba|b\.?eng|m\.?eng|high school)\b",
    re.I,
)
_COMPANY_SUFFIX = re.compile(
    r"\b(inc|llc|ltd|corp|co\.|company|university|college|institute|labs?|"
    r"technologies|systems|group|partners|studio|ai)\b",
    re.I,
)


def normalize_payload(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(data, dict) or not data:
        return None
    payload = dict(data)
    payload["skills"] = normalize_skills(payload.get("skills"))
    payload["experience"] = normalize_roles(payload.get("experience"))
    payload["volunteering"] = normalize_roles(payload.get("volunteering"))
    payload["education"] = normalize_education(payload.get("education"))
    payload["projects"] = _string_list(payload.get("projects"))
    payload["certifications"] = _string_list(payload.get("certifications"))
    payload["languages"] = _string_list(payload.get("languages"))
    payload["honors"] = _string_list(payload.get("honors"))
    payload["websites"] = _string_list(payload.get("websites"))
    for key in ("full_name", "headline", "summary", "email", "location"):
        value = payload.get(key)
        if isinstance(value, str):
            cleaned = _HEADING_PREFIX.sub("", value).strip(" ·•|-")
            payload[key] = cleaned or None
    if payload.get("location"):
        payload["location"] = city_only_location(str(payload["location"]))
    return payload


def city_only_location(value: str | None) -> str | None:
    """Keep a home-base city, dropping school names Nutrient often glues on."""
    if not value:
        return None
    text = re.sub(r"\s+", " ", value).strip(" ,;|")
    if not text:
        return None
    if not _SCHOOL_HINT.search(text):
        return text

    parts = [part.strip() for part in text.split(",") if part.strip()]
    region = parts[-1] if len(parts) >= 2 and _is_region(parts[-1]) else None
    head = parts[:-1] if region else parts
    city_parts = [part for part in head if not _SCHOOL_HINT.search(part)]
    if city_parts:
        city = ", ".join(city_parts)
        return f"{city}, {region}" if region else city

    blob = " ".join(head)
    peeled = re.sub(
        r"^(?:[A-Z][a-z]+\s+)*(?:University|College|Institute|Polytechnic|Academy)"
        r"(?:\s+of\s+[A-Z][a-z]+)?\s*",
        "",
        blob,
        flags=re.I,
    ).strip(" ,")
    if peeled and not _SCHOOL_HINT.search(peeled):
        return f"{peeled}, {region}" if region else peeled
    return None


def _is_region(text: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{2}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", text.strip()))


def normalize_roles(items: Any) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    for item in _as_list(items):
        for blob in _expand_item(item):
            parsed = _parse_role_blob(blob) if isinstance(blob, str) else _parse_role_dict(blob)
            if parsed is None:
                continue
            _absorb_or_append(roles, parsed)
    return _finalize_roles(roles)


def normalize_education(items: Any) -> list[str]:
    lines: list[str] = []
    for item in _as_list(items):
        formatted = _format_education_item(item)
        if not formatted:
            continue
        for piece in _split_education_blob(formatted):
            piece = _strip_junk(piece)
            if not piece or _is_heading(piece) or _is_location(piece) or _is_pdf_junk(piece):
                continue
            for split in _split_glued_schools(piece):
                if lines and _is_education_continuation(lines[-1], split):
                    if split[:1].islower():
                        lines[-1] = f"{lines[-1].rstrip(' ,;')} {split.lstrip(' ,;')}".strip()
                    else:
                        lines[-1] = f"{lines[-1].rstrip(' ·,;')} · {split.lstrip(' ·,;')}".strip()
                else:
                    lines.append(split)
    return _coalesce_education(lines)


def _coalesce_education(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        if merged and _is_school_stub(merged[-1]) and merged[-1].lower() in line.lower():
            merged[-1] = line
            continue
        if merged and _is_school_stub(line) and line.lower() in merged[-1].lower():
            continue
        if merged and _is_date_line(line):
            start, end = _dates_from_text(line)
            dates = " – ".join(part for part in (start, end) if part)
            merged[-1] = f"{merged[-1].rstrip(' ·')} · {dates}"
            continue
        merged.append(line)
    return merged


def _is_school_stub(text: str) -> bool:
    return _looks_like_institution(text) and not _DEGREE_HINT.search(text) and len(text.split()) <= 8


def normalize_skills(items: Any) -> list[str]:
    skills: list[str] = []
    seen: set[str] = set()
    for item in _as_list(items):
        text = _stringify(item)
        if not text:
            continue
        text = _HEADING_PREFIX.sub("", text).strip(" ·•|-")
        parts = re.split(r"[,;/·•|]", text) if any(sep in text for sep in ",;/·•|") else [text]
        for part in parts:
            skill = part.strip(" ·•|-")
            key = skill.lower()
            if not skill or key in _HEADINGS or key in seen or len(skill) > 48:
                continue
            seen.add(key)
            skills.append(skill)
    return skills


def roles_from_plaintext(text: str) -> list[dict[str, Any]]:
    """Fallback when structured extract is empty: split OCR on date spans."""
    section = _slice_section(
        text,
        starts=("experience", "work experience", "employment", "work history", "professional experience"),
        stops=("education", "skills", "volunteering", "projects", "certifications"),
    )
    lines = [line.strip() for line in (section or text).splitlines() if line.strip()]
    return roles_from_resume_lines(lines) or normalize_roles(_split_on_dates(section or text))


def roles_from_resume_lines(lines: list[str]) -> list[dict[str, Any]]:
    """Parse a conventional resume Experience section (headers + hyphen bullets)."""
    roles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw in lines:
        line = raw.strip()
        if not line or _is_heading(line) or _is_pdf_junk(line):
            continue

        if _BULLET_PREFIX.match(line) or (current and _is_prose_fragment(line) and not _DATE_SPAN.search(line)):
            text = _BULLET_PREFIX.sub("", line).strip(" -•*")
            if current and text:
                _append_fragment(current, text)
            continue

        if current and _is_date_line(line):
            start, end = _dates_from_text(line)
            current["start_date"] = current.get("start_date") or start
            current["end_date"] = current.get("end_date") or end
            continue

        if current and _is_location(line):
            if not current.get("location"):
                current["location"] = line
            continue

        if current and _is_open_header(current) and not _looks_like_job_title(line) and not _DATE_SPAN.search(line):
            company, location = _split_company_location(line)
            if not current.get("company"):
                current["company"] = company
            if location and not current.get("location"):
                current["location"] = location
            continue

        parsed = _parse_role_blob(_normalize_resume_header(line))
        if parsed is None:
            if current:
                _append_fragment(current, line)
            continue
        if current and not _is_real_role(parsed) and _is_prose_fragment(line):
            _append_fragment(current, line)
            continue
        if current:
            roles.append(current)
        current = parsed

    if current:
        roles.append(current)
    return _finalize_roles(roles)


def _is_date_line(text: str) -> bool:
    start, end = _dates_from_text(text)
    if not (start or end):
        return False
    remainder = _DATE_SPAN.sub("", text)
    remainder = re.sub(r"\b(?:to|until|present|current|now)\b", "", remainder, flags=re.I)
    remainder = re.sub(r"[\s|·,()–—-]+", "", remainder)
    return len(remainder) < 4


def _is_open_header(role: dict[str, Any]) -> bool:
    return not role.get("bullets") and not (role.get("company") and role.get("start_date"))


def _normalize_resume_header(line: str) -> str:
    return re.sub(r"\s+at\s+", " · ", line, count=1, flags=re.I)


def _split_company_location(line: str) -> tuple[str, str]:
    match = re.search(r",\s*([A-Z][a-zA-Z .]+,\s*[A-Z]{2}(?:[A-Z])?|[A-Z]{2})\s*$", line)
    if not match:
        if _is_location(line):
            return "", line
        return line, ""
    location = match.group(0).lstrip(", ").strip()
    company = line[: match.start()].strip(" ,")
    return company, location


def education_from_plaintext(text: str) -> list[str]:
    section = _slice_section(
        text,
        starts=("education", "academics"),
        stops=("experience", "skills", "volunteering", "projects", "certifications"),
    )
    if not section:
        return []
    return normalize_education(_split_on_dates(section) or [section])


def _expand_item(item: Any) -> list[Any]:
    if isinstance(item, str):
        return _split_on_dates(item) or [item]
    if isinstance(item, dict):
        blob = _dict_as_blob(item)
        if blob and (" · " in blob or _DATE_SPAN.search(blob)):
            pieces = _split_on_dates(blob)
            if len(pieces) > 1:
                return pieces
        return [item]
    return []


def _parse_role_dict(role: dict[str, Any]) -> dict[str, Any] | None:
    title = _stringify(role.get("title"))
    company = _stringify(role.get("company") or role.get("organization") or role.get("employer"))
    start_date = _stringify(role.get("start_date") or role.get("start"))
    end_date = _stringify(role.get("end_date") or role.get("end"))
    location = _stringify(role.get("location"))
    bullets = _collect_bullets(role)

    glued = " · ".join(part for part in (title, company) if part)
    needs_split = (
        (not title or not company)
        or " · " in title
        or " · " in company
        or _DATE_SPAN.search(title)
        or _DATE_SPAN.search(company)
    )
    if needs_split and glued:
        parsed = _parse_role_blob(glued)
        if parsed:
            parsed["bullets"] = _dedupe_keep(parsed.get("bullets", []) + bullets)
            parsed["start_date"] = parsed.get("start_date") or start_date
            parsed["end_date"] = parsed.get("end_date") or end_date
            parsed["location"] = parsed.get("location") or location
            return parsed

    parsed = {
        "title": _strip_heading(title),
        "company": _strip_heading(company),
        "start_date": start_date,
        "end_date": end_date,
        "location": location,
        "bullets": bullets,
    }
    _fill_dates_from_text(parsed, " ".join(part for part in (title, company, location) if part))
    return parsed


def _parse_role_blob(text: str) -> dict[str, Any] | None:
    cleaned = _HEADING_PREFIX.sub("", _normalize_resume_header(text)).strip(" ·•|-")
    if not cleaned or _is_heading(cleaned):
        return None

    start_date, end_date = _dates_from_text(cleaned)
    date_match = _DATE_SPAN.search(cleaned)
    before = cleaned[: date_match.start()].strip(" ·•|-") if date_match else cleaned
    after = cleaned[date_match.end() :].strip(" ·•|-") if date_match else ""
    after = _DURATION.sub("", after).strip(" ·•|-")

    before_parts = _meaningful_parts(before)
    after_parts = _meaningful_parts(after)

    title = ""
    company = ""
    location_parts: list[str] = []
    bullets: list[str] = []
    preamble: list[str] = []

    kinds = _annotate_locations(before_parts)
    names: list[str] = []
    for part, kind in zip(before_parts, kinds, strict=True):
        if kind == "heading":
            continue
        if kind == "location":
            preamble.append(part)
        elif kind == "bullet":
            preamble.append(part)
        elif kind == "title" and not title:
            title = part
        else:
            names.append(part)

    if not title:
        title_idx = next((i for i, part in enumerate(names) if _looks_like_title(part)), None)
        if title_idx is not None:
            title = names.pop(title_idx)
    if names:
        company = names.pop()
        preamble.extend(names)

    after_kinds = _annotate_locations(after_parts)
    for part, kind in zip(after_parts, after_kinds, strict=True):
        if kind == "location":
            location_parts.append(part)
        elif kind == "heading":
            continue
        elif kind == "bullet" or len(part) > 40:
            bullets.append(part)
        elif not company:
            company = part
        elif not title and _looks_like_title(part):
            title = part
        else:
            bullets.append(part)

    return {
        "title": title,
        "company": company,
        "start_date": start_date,
        "end_date": end_date,
        "location": _format_location(location_parts),
        "bullets": _dedupe_keep(bullets),
        "_preamble": preamble,
    }


def _absorb_or_append(roles: list[dict[str, Any]], incoming: dict[str, Any]) -> None:
    """Attach description/location fragments to the previous job instead of a new row."""
    preamble = [part for part in incoming.pop("_preamble", []) if part]
    loc_bits = [part for part in preamble if _is_location(part) or _looks_like_city(part)]
    extra_bits = [part for part in preamble if part not in loc_bits]

    if roles and not _is_real_role(incoming):
        previous = roles[-1]
        if loc_bits and not previous.get("location"):
            previous["location"] = _format_location(loc_bits)
        for part in extra_bits:
            _append_fragment(previous, part)
        _merge_role(previous, incoming)
        return

    if roles:
        previous = roles[-1]
        if loc_bits and not previous.get("location"):
            previous["location"] = _format_location(loc_bits)
        for part in extra_bits:
            _append_fragment(previous, part)
    elif loc_bits and not incoming.get("location"):
        incoming["location"] = _format_location(loc_bits)

    roles.append(incoming)


def _orphan_text(role: dict[str, Any]) -> list[str]:
    bits = [role.get("title") or "", role.get("company") or ""]
    return [
        bit
        for bit in bits
        if bit and not _is_heading(bit) and not _is_location(bit) and not _is_pdf_junk(bit)
    ]


def _merge_role(dest: dict[str, Any], src: dict[str, Any]) -> None:
    if src.get("location") and not dest.get("location"):
        dest["location"] = src["location"]
    for text in src.get("bullets", []) + _orphan_text(src):
        _append_fragment(dest, text)


def _append_fragment(role: dict[str, Any], text: str) -> None:
    cleaned = _strip_junk(text)
    if not cleaned or _is_heading(cleaned) or _is_pdf_junk(cleaned):
        return
    if _is_location(cleaned):
        if not role.get("location"):
            role["location"] = cleaned
        return
    bullets = role.setdefault("bullets", [])
    if bullets and _is_wrap_continuation(bullets[-1], cleaned):
        bullets[-1] = _join_wrap(bullets[-1], cleaned)
        return
    if cleaned not in bullets:
        bullets.append(cleaned)


def _finalize_roles(roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finalized: list[dict[str, Any]] = []
    for role in roles:
        role["title"] = _strip_junk(role.get("title") or "")
        role["company"] = _strip_junk(role.get("company") or "")
        role["location"] = _strip_junk(role.get("location") or "")
        kept: list[str] = []
        for bullet in role.get("bullets") or []:
            cleaned = _strip_junk(bullet)
            if not cleaned or _is_heading(cleaned) or _is_pdf_junk(cleaned):
                continue
            if _is_location(cleaned):
                if not role.get("location"):
                    role["location"] = cleaned
                continue
            if kept and _is_wrap_continuation(kept[-1], cleaned):
                kept[-1] = _join_wrap(kept[-1], cleaned)
            else:
                kept.append(cleaned)
        role["bullets"] = kept
        if finalized and not _is_real_role(role):
            _merge_role(finalized[-1], role)
            continue
        finalized.append(role)
    return [
        {key: value for key, value in role.items() if not str(key).startswith("_")}
        for role in finalized
        if _is_real_role(role)
    ]


def _is_real_role(role: dict[str, Any]) -> bool:
    title = _strip_junk(role.get("title") or "")
    company = _strip_junk(role.get("company") or "")
    if _is_heading(title) or _is_heading(company) or _is_pdf_junk(title) or _is_pdf_junk(company):
        return False
    if _is_prose_fragment(title) or _is_prose_fragment(company):
        return False
    if _is_location(title) or _is_location(company):
        return False
    if _looks_like_job_title(title):
        return True
    has_dates = bool(role.get("start_date") or role.get("end_date"))
    if company and has_dates and _is_short_name(company) and (not title or _is_short_name(title)):
        return True
    return False


def _is_short_name(text: str) -> bool:
    words = text.split()
    return bool(text) and 1 <= len(words) <= 8 and not _is_prose_fragment(text)


def _format_education_item(item: Any) -> str:
    if isinstance(item, str):
        return _strip_heading(item)
    if not isinstance(item, dict):
        return ""
    school = _stringify(item.get("school") or item.get("institution") or item.get("university"))
    degree = _stringify(item.get("degree"))
    field = _stringify(item.get("field") or item.get("field_of_study") or item.get("major"))
    start = _stringify(item.get("start_date"))
    end = _stringify(item.get("end_date") or item.get("dates") or item.get("year"))
    if start and end:
        dates = f"{start} - {end}"
    else:
        dates = end or start
    if degree and field and field.lower() not in degree.lower():
        degree = f"{degree}, {field}"
    elif field and not degree:
        degree = field
    parts = [part for part in (degree, school, dates) if part and not _is_heading(part) and not _is_pdf_junk(part)]
    if parts:
        return " · ".join(parts)
    return _strip_heading(_stringify(item.get("title") or item.get("name")))


def _split_education_blob(text: str) -> list[str]:
    if _DATE_SPAN.search(text) and " · " in text:
        pieces = _split_on_dates(text)
        if len(pieces) > 1:
            return [_strip_heading(piece) for piece in pieces if _strip_heading(piece)]
    return [_strip_heading(text)] if _strip_heading(text) else []


def _is_education_continuation(previous: str, current: str) -> bool:
    if _is_pdf_junk(current):
        return False
    if current[:1].islower():
        return True
    prev_inst = _looks_like_institution(previous)
    curr_inst = _looks_like_institution(current)
    prev_degree = bool(_DEGREE_HINT.search(previous))
    curr_degree = bool(_DEGREE_HINT.search(current))
    if curr_inst and prev_inst:
        return False
    if curr_inst and prev_degree and not prev_inst:
        return True
    if prev_inst and curr_degree and not curr_inst:
        return True
    return False


def _looks_like_institution(text: str) -> bool:
    stripped = text.strip().strip(" ·,;")
    if re.fullmatch(r"High School(?: Diploma)?", stripped, re.I):
        return False
    return bool(_institution_matches(stripped))


def _institution_matches(text: str) -> list[str]:
    names: list[str] = []
    for match in _INSTITUTION.finditer(text):
        name = match.group(0).strip()
        if re.fullmatch(r"High School", name, re.I):
            continue
        names.append(name)
    return names


def _split_glued_schools(text: str) -> list[str]:
    spans = [
        match
        for match in _INSTITUTION.finditer(text)
        if not re.fullmatch(r"High School", match.group(0).strip(), re.I)
    ]
    if len(spans) < 2:
        return [text]
    second = spans[1]
    left = text[: second.start()].strip(" ·,;")
    right = text[second.start() :].strip(" ·,;")
    return [part for part in (left, right) if part]


def _collect_bullets(role: dict[str, Any]) -> list[str]:
    bullets: list[str] = []
    for key in ("bullets", "highlights", "responsibilities"):
        for item in _as_list(role.get(key)):
            text = _stringify(item)
            if text:
                bullets.append(text)
    description = _stringify(role.get("description") or role.get("summary"))
    if description:
        for line in re.split(r"[\n•]", description):
            cleaned = line.strip(" -•*")
            if cleaned:
                bullets.append(cleaned)
    return _dedupe_keep(bullets)


def _split_on_dates(text: str) -> list[str]:
    matches = list(_DATE_SPAN.finditer(text))
    if not matches:
        return [text.strip()] if text.strip() else []
    chunks: list[str] = []
    cursor = 0
    for match in matches:
        end = match.end()
        duration = _DURATION.match(text, end)
        if duration:
            end = duration.end()
        chunk = text[cursor:end].strip(" \n·•|-")
        if chunk:
            chunks.append(chunk)
        cursor = end
    tail = text[cursor:].strip(" \n·•|-")
    if tail:
        if chunks:
            chunks[-1] = f"{chunks[-1]} · {tail}"
        else:
            chunks.append(tail)
    return chunks


def _slice_section(text: str, starts: tuple[str, ...], stops: tuple[str, ...]) -> str:
    start_re = re.compile(rf"(?im)^(?:{'|'.join(re.escape(name) for name in starts)})\s*$")
    stop_re = re.compile(rf"(?im)^(?:{'|'.join(re.escape(name) for name in stops)})\s*$")
    lines = text.splitlines()
    begin = None
    end = len(lines)
    for index, line in enumerate(lines):
        if begin is None and start_re.match(line.strip().rstrip(":")):
            begin = index + 1
            continue
        if begin is not None and stop_re.match(line.strip().rstrip(":")):
            end = index
            break
    if begin is None:
        return ""
    return "\n".join(lines[begin:end]).strip()


def _meaningful_parts(text: str) -> list[str]:
    parts = _MIDDOT_SPLIT.split(text) if text else []
    cleaned = []
    for part in parts:
        value = part.strip(" ·•|-")
        if value and not _is_heading(value) and not _DURATION.fullmatch(value):
            cleaned.append(value)
    return cleaned


def _annotate_locations(parts: list[str]) -> list[str]:
    kinds = [_classify(part) for part in parts]
    original = list(kinds)
    for index, kind in enumerate(original):
        if kind != "location":
            continue
        for neighbor in (index - 1, index + 1):
            if 0 <= neighbor < len(parts) and kinds[neighbor] == "name" and _looks_like_city(parts[neighbor]):
                kinds[neighbor] = "location"
    return kinds


def _classify(part: str) -> str:
    if _is_heading(part):
        return "heading"
    if _DATE_SPAN.search(part) or _DURATION.fullmatch(part.strip()):
        return "date"
    if _is_location(part):
        return "location"
    if _looks_like_sentence(part):
        return "bullet"
    if _looks_like_title(part):
        return "title"
    return "name"


def _looks_like_city(text: str) -> bool:
    stripped = text.strip()
    if _looks_like_title(stripped) or _looks_like_sentence(stripped):
        return False
    return bool(re.fullmatch(r"[A-Z][a-z]+(?:[\s-][A-Z][a-z]+)?", stripped))


def _format_location(parts: list[str]) -> str:
    cleaned = _dedupe_keep(parts)
    if cleaned and re.fullmatch(r"[A-Z]{2}", cleaned[0]) and len(cleaned) > 1:
        cleaned = cleaned[1:] + cleaned[:1]
    return ", ".join(cleaned)


def _looks_like_title(text: str) -> bool:
    return _looks_like_job_title(text)


def _looks_like_job_title(text: str) -> bool:
    cleaned = _strip_junk(text)
    if not cleaned or _is_prose_fragment(cleaned) or _is_pdf_junk(cleaned):
        return False
    words = cleaned.split()
    if not 1 <= len(words) <= 7:
        return False
    lowered = cleaned.lower()
    return any(re.search(rf"\b{re.escape(hint)}\b", lowered) for hint in _TITLE_HINTS)


def _looks_like_sentence(text: str) -> bool:
    return _is_prose_fragment(text)


def _is_prose_fragment(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped[:1].islower():
        return True
    if stripped.endswith((",", ";", ":", "-", "—")):
        return True
    words = re.findall(r"[A-Za-z']+", stripped)
    if len(words) >= 8:
        return True
    stops = sum(1 for word in words if word.lower() in _PROSE_STOPWORDS)
    if len(words) >= 5 and stops >= 2:
        return True
    if stripped.endswith(".") and len(words) >= 6:
        return True
    return bool(
        re.match(
            r"^(built|developed|led|created|designed|implemented|improved|managed|"
            r"owned|reduced|increased|collaborated|contributed|worked|ran)\b",
            stripped,
            re.I,
        )
    )


def _is_wrap_continuation(previous: str, current: str) -> bool:
    prev = previous.rstrip()
    cur = current.lstrip()
    if not prev or not cur:
        return False
    if cur[:1].islower():
        return True
    if prev.endswith("-") and cur[:1].islower():
        return True
    if prev[-1:] in ",;:":
        return True
    return False


def _join_wrap(left: str, right: str) -> str:
    prev = left.rstrip()
    cur = right.lstrip()
    if prev.endswith("-"):
        return prev[:-1] + cur
    return f"{prev} {cur}"


def _is_pdf_junk(text: str) -> bool:
    stripped = text.strip()
    return bool(_PDF_JUNK.fullmatch(stripped) or _PDF_JUNK.search(stripped) and len(stripped.split()) <= 6)


def _strip_junk(text: str) -> str:
    if not text:
        return ""
    cleaned = _PDF_JUNK.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ·•|")


def _is_heading(text: str) -> bool:
    return text.strip().rstrip(":").lower() in _HEADINGS


def _is_location(text: str) -> bool:
    stripped = text.strip().rstrip(".")
    if not stripped or _COMPANY_SUFFIX.search(stripped):
        return False
    if re.fullmatch(r"(?:remote|hybrid|on-?site)(?:\s*\([^)]+\))?", stripped, re.I):
        return True
    if re.fullmatch(r"[A-Z]{2}", stripped):
        return True
    if re.match(r"^Greater\s+\w+(?:\s+\w+)?\s+Area\b", stripped, re.I):
        return True
    if re.fullmatch(r"[A-Z][a-z]+(?:[\s-][A-Z][a-z]+)*,\s*(?:[A-Z]{2}|[A-Z][a-z]+)(?:,\s*[A-Z][a-z]+)?", stripped):
        return True
    return False


def _strip_heading(text: str) -> str:
    return _HEADING_PREFIX.sub("", text).strip(" ·•|-") if text else ""


def _dates_from_text(text: str) -> tuple[str, str]:
    match = _DATE_SPAN.search(text or "")
    if not match:
        return "", ""
    span = match.group(1) or match.group(0)
    parts = re.split(r"\s*(?:[-–—]|to)\s*", span, maxsplit=1, flags=re.I)
    if len(parts) >= 2:
        return _pretty_date(parts[0]), _pretty_date(parts[1])
    return _pretty_date(parts[0]), ""


def _pretty_date(value: str) -> str:
    cleaned = value.strip(" ()")
    if re.fullmatch(r"present|current|now", cleaned, re.I):
        return cleaned.title()
    return cleaned


def _fill_dates_from_text(role: dict[str, Any], text: str) -> None:
    if role.get("start_date") and role.get("end_date"):
        return
    start, end = _dates_from_text(text)
    role["start_date"] = role.get("start_date") or start
    role["end_date"] = role.get("end_date") or end


def _dict_as_blob(role: dict[str, Any]) -> str:
    parts = [
        _stringify(role.get("title")),
        _stringify(role.get("company")),
        _stringify(role.get("start_date")),
        _stringify(role.get("end_date")),
        _stringify(role.get("location")),
    ]
    return " · ".join(part for part in parts if part)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _strip_junk(value)
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _string_list(value: Any) -> list[str]:
    return [_stringify(item) for item in _as_list(value) if _stringify(item) and not _is_heading(_stringify(item))]


def _dedupe_keep(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value.strip())
    return result
