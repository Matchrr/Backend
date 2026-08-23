"""Nutrient DWS: OCR + structured extraction for LinkedIn PDFs and resumes.

Two calls, one job:

1. POST /build with json-content — OCR + plaintext. This is the attested source.
2. POST /extraction/extract with our career schema — structured fields for the
   Ground Truth card, so we are not regex-parsing two-column LinkedIn PDFs.

If the API key is missing, callers fall back to local pypdf. Never log the key.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings
from app.services.career_parse import normalize_payload as _normalize_career

BUILD_URL = "https://api.nutrient.io/build"
EXTRACT_URL = "https://api.nutrient.io/extraction/extract"

RESUME_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "full_name": {
            "type": "string",
            "description": "The person's full name from the header. Not a section title.",
        },
        "headline": {
            "type": "string",
            "description": "One-line professional headline under the name, if present.",
        },
        "email": {"type": "string", "description": "Email address if printed"},
        "location": {
            "type": "string",
            "description": (
                "Home-base city and region from the header only, e.g. Waterloo, ON. "
                "Never a university, college, or school name. Never a job location line."
            ),
        },
        "summary": {
            "type": "string",
            "description": "About / summary paragraph. Not skills, not job descriptions.",
        },
        "websites": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Personal, GitHub, or portfolio URLs",
        },
        "skills": {
            "type": "array",
            "description": "Individual skill names only. One array item per skill, e.g. Python, not 'SKILLS Python'.",
            "items": {"type": "string"},
        },
        "experience": {
            "type": "array",
            "description": (
                "One object per paid job or internship. Traditional resumes list title, "
                "employer, dates, then hyphen bullets. LinkedIn PDFs list title, company, "
                "dates, city, then a wrapped paragraph. Either way: one object per job. "
                "Hyphen/bullet lines and wrapped description lines belong on that same "
                "object. Ignore section headers and page numbers."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Job title only, e.g. Software Engineer. Never the company or dates.",
                    },
                    "company": {
                        "type": "string",
                        "description": "Employer name only, e.g. Nimble. Never the title or dates.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start month and year, e.g. September 2025",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End month and year, or Present",
                    },
                    "location": {
                        "type": "string",
                        "description": "Workplace city for this role, e.g. Toronto, ON",
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "The role write-up that follows the dates and city. Keep it on this "
                            "job. Never turn this paragraph into a separate experience item."
                        ),
                    },
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Achievement bullets for this role only, one sentence per item.",
                    },
                },
            },
        },
        "education": {
            "type": "array",
            "description": "One object per school. Do not split a degree across two items.",
            "items": {
                "type": "object",
                "properties": {
                    "school": {"type": "string", "description": "Institution name only"},
                    "degree": {
                        "type": "string",
                        "description": "Degree name only, e.g. Bachelor of Science",
                    },
                    "field": {
                        "type": "string",
                        "description": "Field of study only, e.g. Computer Science",
                    },
                    "end_date": {"type": "string", "description": "Graduation year or date range if printed"},
                    "start_date": {"type": "string", "description": "Start year if printed"},
                },
                "required": ["school"],
            },
        },
        "certifications": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Certificate names, one per item",
        },
        "volunteering": {
            "type": "array",
            "description": "One object per volunteer role, same shape as experience",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Volunteer role title only"},
                    "company": {"type": "string", "description": "Organization name only"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": "Volunteer write-up for this role only. Never a new volunteering item.",
                    },
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "company"],
            },
        },
        "projects": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Project name and a short description as one string",
        },
        "languages": {"type": "array", "items": {"type": "string"}},
        "honors": {"type": "array", "items": {"type": "string"}},
    },
}

EXTRACT_GUIDANCE = (
    "This is a resume, or a LinkedIn Save-to-PDF of a resume. "
    "Traditional resumes: each job is a title, an employer, a date range "
    "(including formats like '2022 – 2024', 'Sept 2022 to Present', '09/2022-05/2024'), "
    "then hyphen or bullet achievements. Every hyphen line is a bullet on that same job. "
    "LinkedIn PDFs: title, company, dates, city, then a wrapped paragraph; wrapped lines "
    "that start lowercase or continue a sentence are still that job's description. "
    "Never create a new experience object for a bullet, a city, a date line, or "
    "'Page 1 of 1'. Education: one object per school. Skills: individual names only."
)


class NutrientError(Exception):
    def __init__(self, message: str, *, code: str = "nutrient_error") -> None:
        super().__init__(message)
        self.code = code


def is_configured() -> bool:
    return bool(settings.nutrient_api_key.strip())


def ingest_pdf(payload: bytes, filename: str = "resume.pdf") -> tuple[str, dict[str, Any] | None]:
    """Return (plaintext, structured payload or None)."""
    if not is_configured():
        raise NutrientError("Nutrient is not configured.", code="not_configured")
    if payload[:5] != b"%PDF-":
        raise NutrientError("Nutrient ingest expects a PDF.", code="not_pdf")

    text = ""
    try:
        text = extract_plaintext(payload, filename)
    except NutrientError:
        text = ""
    structured = extract_structured(payload, filename)
    if not text.strip() and not structured:
        raise NutrientError("Nutrient could not read that PDF.", code="empty")
    return text, structured


def extract_plaintext(payload: bytes, filename: str = "resume.pdf") -> str:
    instructions = {
        "parts": [{"file": "document"}],
        "actions": [{"type": "ocr", "language": "english"}],
        "output": {
            "type": "json-content",
            "plainText": True,
            "structuredText": False,
            "keyValuePairs": False,
            "tables": False,
        },
    }
    body = _post_multipart(
        BUILD_URL,
        payload,
        filename,
        extra_form={"instructions": json.dumps(instructions)},
        timeout=90.0,
    )
    return _plain_text_from_build(body)


def extract_structured(payload: bytes, filename: str = "resume.pdf") -> dict[str, Any] | None:
    instructions = {
        "schema": RESUME_SCHEMA,
        "parseConfig": {"mode": "understand"},
        "instructions": EXTRACT_GUIDANCE,
    }
    try:
        body = _post_multipart(
            EXTRACT_URL,
            payload,
            filename,
            extra_form={"instructions": json.dumps(instructions)},
            timeout=120.0,
        )
    except NutrientError:
        return None

    data = _unwrap_extract(body)
    return _normalize_career(data) if data else None


def _unwrap_extract(body: Any) -> dict[str, Any] | None:
    if not isinstance(body, dict):
        return None
    data = _nested(body, "output", "data")
    if isinstance(data, dict) and data:
        return data
    output = body.get("output")
    if isinstance(output, dict):
        nested = output.get("data")
        if isinstance(nested, dict) and nested:
            return nested
        if _looks_like_career(output):
            return output
    if _looks_like_career(body):
        return body
    return None


def _looks_like_career(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in ("experience", "education", "skills", "full_name", "headline", "summary")
    )


def _post_multipart(
    url: str,
    payload: bytes,
    filename: str,
    extra_form: dict[str, str],
    timeout: float,
) -> Any:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {settings.nutrient_api_key}"},
                files={"file": (filename, payload, "application/pdf")},
                data=extra_form,
            )
    except httpx.HTTPError as exc:
        raise NutrientError("Could not reach Nutrient.", code="network") from exc

    if response.status_code >= 400:
        raise NutrientError(
            _error_message(response, "Nutrient could not read that PDF."),
            code="http_error",
        )
    try:
        return response.json()
    except ValueError as exc:
        raise NutrientError("Nutrient returned a non-JSON body.", code="bad_payload") from exc


def _plain_text_from_build(body: Any) -> str:
    if isinstance(body, str):
        return body.strip()
    if not isinstance(body, dict):
        return ""

    pages = body.get("pages")
    if isinstance(pages, list):
        chunks = [_page_text(page) for page in pages]
        joined = "\n".join(chunk for chunk in chunks if chunk)
        if joined.strip():
            return joined.strip()

    for key in ("plainText", "text", "markdown"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    nested = _nested(body, "output")
    if nested is not None and nested is not body:
        return _plain_text_from_build(nested)
    return ""


def _page_text(page: Any) -> str:
    if isinstance(page, str):
        return page.strip()
    if not isinstance(page, dict):
        return ""
    for key in ("plainText", "text", "markdown"):
        value = page.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _nested(body: Any, *keys: str) -> Any:
    current = body
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        body = response.json()
    except ValueError:
        return fallback
    if not isinstance(body, dict):
        return fallback
    for key in ("message", "error", "detail"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    details = body.get("details")
    if isinstance(details, str) and details.strip():
        return details.strip()
    return fallback
