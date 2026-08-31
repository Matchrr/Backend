"""Sign In with LinkedIn (OpenID) plus optional Member Data Portability.

LinkedIn's self-serve OpenID product returns identity: name, email, photo.
Experience, education, skills, and volunteering are not in that payload.

The optional DMA Member Snapshot API can return a full résumé-like export, but
only for members in the EEA/Switzerland whose app has that product enabled.
We try it when the extra scope is configured and swallow failures so OpenID
still grounds personal identity.

Never scrape LinkedIn. Never log access tokens.
"""

from __future__ import annotations

import re
import secrets
import threading
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SNAPSHOT_URL = "https://api.linkedin.com/rest/memberSnapshotData"

# Career-relevant DMA snapshot domains. Case-sensitive per LinkedIn docs.
SNAPSHOT_DOMAINS = (
    "PROFILE",
    "POSITIONS",
    "EDUCATION",
    "SKILLS",
    "CERTIFICATIONS",
    "PROJECTS",
    "VOLUNTEERING_EXPERIENCES",
    "LANGUAGES",
    "HONORS",
    "PUBLICATIONS",
)

OPENID_SCOPES = ("openid", "profile", "email")
STATE_TTL_SECONDS = 600
SNAPSHOT_VERSION = "202312"


class LinkedInError(Exception):
    def __init__(self, message: str, *, code: str = "linkedin_error") -> None:
        super().__init__(message)
        self.code = code


class _PendingAuth:
    __slots__ = ("created_at", "user_id")

    def __init__(self, user_id: str | None = None) -> None:
        self.created_at = time.time()
        self.user_id = user_id


_pending: dict[str, _PendingAuth] = {}
_lock = threading.Lock()


def is_configured() -> bool:
    return bool(settings.linkedin_client_id and settings.linkedin_client_secret)


def requested_scopes() -> list[str]:
    scopes = list(OPENID_SCOPES)
    extra = settings.linkedin_dma_scope.strip()
    if extra:
        for scope in extra.split():
            if scope not in scopes:
                scopes.append(scope)
    return scopes


def build_authorization_url(user_id: str | None = None) -> str:
    if not is_configured():
        raise LinkedInError(
            "LinkedIn is not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET.",
            code="not_configured",
        )

    state = secrets.token_urlsafe(24)

    with _lock:
        _evict_expired_locked()
        _pending[state] = _PendingAuth(user_id=user_id)

    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "state": state,
        "scope": " ".join(requested_scopes()),
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def complete_login(
    code: str | None, state: str | None
) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """Exchange the OAuth code and return (profile_payload, token_bundle, owner_user_id)."""
    if not code or not state:
        raise LinkedInError("LinkedIn did not return an authorization code.", code="missing_code")

    with _lock:
        pending = _pending.pop(state, None)
        _evict_expired_locked()

    if pending is None or time.time() - pending.created_at > STATE_TTL_SECONDS:
        raise LinkedInError("This LinkedIn sign-in expired. Please try again.", code="invalid_state")

    tokens = _exchange_code(code)
    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise LinkedInError("LinkedIn did not return an access token.", code="token_failed")

    identity = _fetch_userinfo(access_token)
    payload = _payload_from_userinfo(identity)

    snapshot = _fetch_snapshot(access_token)
    if snapshot:
        _merge_snapshot(payload, snapshot)

    return payload, tokens, pending.user_id


def fetch_profile_with_token(access_token: str) -> dict[str, Any]:
    identity = _fetch_userinfo(access_token)
    payload = _payload_from_userinfo(identity)
    snapshot = _fetch_snapshot(access_token)
    if snapshot:
        _merge_snapshot(payload, snapshot)
    return payload


def _evict_expired_locked() -> None:
    cutoff = time.time() - STATE_TTL_SECONDS
    stale = [key for key, value in _pending.items() if value.created_at < cutoff]
    for key in stale:
        _pending.pop(key, None)


def _exchange_code(code: str) -> dict[str, Any]:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.linkedin_redirect_uri,
        "client_id": settings.linkedin_client_id,
        "client_secret": settings.linkedin_client_secret,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        raise LinkedInError("Could not reach LinkedIn to finish sign-in.", code="network") from exc

    if response.status_code >= 400:
        raise LinkedInError(
            _linkedin_error_message(response, "LinkedIn refused the sign-in."),
            code="token_failed",
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise LinkedInError("LinkedIn returned an unexpected token payload.", code="token_failed")
    return payload


def _fetch_userinfo(access_token: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise LinkedInError("Could not load your LinkedIn identity.", code="network") from exc

    if response.status_code >= 400:
        raise LinkedInError(
            _linkedin_error_message(response, "LinkedIn did not return your profile identity."),
            code="userinfo_failed",
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise LinkedInError("LinkedIn identity payload was empty.", code="userinfo_failed")
    return payload


def _fetch_snapshot(access_token: str) -> dict[str, list[dict[str, Any]]]:
    """Best-effort DMA snapshot. Returns {} when the product/scope/region blocks it."""
    collected: dict[str, list[dict[str, Any]]] = {}
    for domain in SNAPSHOT_DOMAINS:
        rows = _fetch_snapshot_domain(access_token, domain)
        if rows:
            collected[domain] = rows
    return collected


def _fetch_snapshot_domain(access_token: str, domain: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    for _ in range(20):
        params = {"q": "criteria", "domain": domain, "start": start, "count": 50}
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    SNAPSHOT_URL,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Linkedin-Version": SNAPSHOT_VERSION,
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                )
        except httpx.HTTPError:
            return rows

        if response.status_code in {401, 403, 404, 426}:
            return rows
        if response.status_code >= 400:
            return rows

        body = response.json()
        elements = body.get("elements") if isinstance(body, dict) else None
        if not isinstance(elements, list):
            return rows

        page_rows: list[dict[str, Any]] = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            data = element.get("snapshotData")
            if isinstance(data, list):
                page_rows.extend(item for item in data if isinstance(item, dict))

        if not page_rows:
            break
        rows.extend(page_rows)

        paging = body.get("paging") if isinstance(body, dict) else None
        next_href = _next_page_href(paging)
        if not next_href:
            break
        start += 1
    return rows


def _next_page_href(paging: Any) -> str | None:
    if not isinstance(paging, dict):
        return None
    links = paging.get("links")
    if not isinstance(links, list):
        return None
    for link in links:
        if isinstance(link, dict) and link.get("rel") == "next":
            href = link.get("href")
            return href if isinstance(href, str) and href else None
    return None


def _payload_from_userinfo(identity: dict[str, Any]) -> dict[str, Any]:
    given = _text(identity.get("given_name"))
    family = _text(identity.get("family_name"))
    name = _text(identity.get("name")) or " ".join(part for part in (given, family) if part)
    locale = identity.get("locale")
    locale_text = ""
    if isinstance(locale, dict):
        locale_text = f"{locale.get('language', '')}_{locale.get('country', '')}".strip("_")
    elif isinstance(locale, str):
        locale_text = locale

    return {
        "linkedin_member_id": _text(identity.get("sub")),
        "full_name": name or None,
        "given_name": given or None,
        "family_name": family or None,
        "email": _text(identity.get("email")) or None,
        "picture": _text(identity.get("picture")) or None,
        "locale": locale_text or None,
        "headline": None,
        "summary": None,
        "location": None,
        "websites": [],
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "volunteering": [],
        "projects": [],
        "honors": [],
        "languages": [],
    }


def _merge_snapshot(payload: dict[str, Any], snapshot: dict[str, list[dict[str, Any]]]) -> None:
    profile_rows = snapshot.get("PROFILE") or []
    if profile_rows:
        _apply_profile_row(payload, profile_rows[0])

    payload["experience"] = [
        role for role in (_map_position(row) for row in snapshot.get("POSITIONS") or []) if role
    ]
    payload["education"] = [
        line for line in (_map_education(row) for row in snapshot.get("EDUCATION") or []) if line
    ]
    payload["skills"] = [
        skill for skill in (_map_named(row, "Name", "Skill", "Skill Name") for row in snapshot.get("SKILLS") or []) if skill
    ]
    payload["certifications"] = [
        line for line in (_map_certification(row) for row in snapshot.get("CERTIFICATIONS") or []) if line
    ]
    payload["volunteering"] = [
        role for role in (_map_volunteer(row) for row in snapshot.get("VOLUNTEERING_EXPERIENCES") or []) if role
    ]
    payload["projects"] = [
        line for line in (_map_project(row) for row in snapshot.get("PROJECTS") or []) if line
    ]
    payload["honors"] = [
        honor for honor in (_map_named(row, "Title", "Name") for row in snapshot.get("HONORS") or []) if honor
    ]
    payload["languages"] = [
        lang for lang in (_map_language(row) for row in snapshot.get("LANGUAGES") or []) if lang
    ]


def _apply_profile_row(payload: dict[str, Any], row: dict[str, Any]) -> None:
    first = _pick(row, "First Name", "FirstName")
    last = _pick(row, "Last Name", "LastName")
    assembled = " ".join(part for part in (first, last) if part)
    payload["full_name"] = payload.get("full_name") or assembled or None
    payload["headline"] = _pick(row, "Headline") or None
    payload["summary"] = _pick(row, "Summary", "About") or None
    payload["location"] = (
        _pick(row, "Geo Location", "Location", "Address")
        or _join_location(_pick(row, "Zip Code"), _pick(row, "Geo Location"))
        or None
    )
    websites = _split_list(_pick(row, "Websites", "Website"))
    if websites:
        payload["websites"] = websites
    industry = _pick(row, "Industry")
    if industry and not payload.get("headline"):
        payload["headline"] = industry


def _map_position(row: dict[str, Any]) -> dict[str, Any] | None:
    title = _pick(row, "Title", "Position", "Job Title")
    company = _pick(row, "Company Name", "Company", "Employer")
    if not title and not company:
        return None
    description = _pick(row, "Description", "Job Description", "Summary")
    return {
        "title": title or "",
        "company": company or "",
        "start_date": _year(_pick(row, "Started On", "Start Date", "StartDate")),
        "end_date": _end_date(_pick(row, "Finished On", "End Date", "EndDate")),
        "bullets": _as_bullets(description),
    }


def _map_volunteer(row: dict[str, Any]) -> dict[str, Any] | None:
    title = _pick(row, "Role", "Title", "Position")
    organization = _pick(row, "Organization", "Company Name", "Company")
    if not title and not organization:
        return None
    description = _pick(row, "Description", "Cause")
    cause = _pick(row, "Cause")
    bullets = _as_bullets(description)
    if cause and cause not in " ".join(bullets):
        bullets.insert(0, cause)
    return {
        "title": title or "",
        "company": organization or "",
        "start_date": _year(_pick(row, "Started On", "Start Date")),
        "end_date": _end_date(_pick(row, "Finished On", "End Date")),
        "bullets": bullets,
    }


def _map_education(row: dict[str, Any]) -> str | None:
    school = _pick(row, "School Name", "School", "Institution")
    degree = _pick(row, "Degree Name", "Degree", "Notes")
    field = _pick(row, "Field Of Study", "Field of Study", "Field")
    credential_parts = [degree] if degree else []
    if field and field.lower() not in degree.lower():
        credential_parts.append(field)
    credential = ", ".join(credential_parts)
    year = _year(_pick(row, "Finished On", "End Date", "EndDate", "Started On"))
    parts = [part for part in (credential, school) if part]
    if not parts:
        return None
    line = ", ".join(parts)
    return f"{line} ({year})" if year else line


def _map_certification(row: dict[str, Any]) -> str | None:
    name = _pick(row, "Name", "Title", "Certification Name")
    if not name:
        return None
    authority = _pick(row, "Authority", "Company Name", "Issuer")
    return f"{name} ({authority})" if authority else name


def _map_project(row: dict[str, Any]) -> str | None:
    name = _pick(row, "Title", "Name", "Project Name")
    if not name:
        return None
    description = _pick(row, "Description", "Summary")
    url = _pick(row, "Url", "URL", "Website")
    detail = description or url
    if detail:
        snippet = detail.splitlines()[0].strip()
        if len(snippet) > 160:
            snippet = snippet[:157] + "..."
        return f"{name} — {snippet}"
    return name


def _map_language(row: dict[str, Any]) -> str | None:
    name = _pick(row, "Name", "Language")
    if not name:
        return None
    proficiency = _pick(row, "Proficiency", "Level")
    return f"{name} ({proficiency})" if proficiency else name


def _map_named(row: dict[str, Any], *keys: str) -> str | None:
    return _pick(row, *keys) or None


def _pick(row: dict[str, Any], *keys: str) -> str:
    lower = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            value = lower.get(key.lower())
        text = _text(value)
        if text:
            return text
    return ""


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def _split_list(value: str) -> list[str]:
    if not value:
        return []
    parts = [part.strip() for part in value.replace(";", ",").split(",")]
    return [part for part in parts if part]


def _join_location(*parts: str) -> str:
    return ", ".join(part for part in parts if part)


def _year(value: str) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    if stripped.lower() in {"present", "current", "now"}:
        return "Present"
    found = re.search(r"(19|20)\d{2}", stripped)
    return found.group(0) if found else stripped


def _end_date(value: str) -> str | None:
    if not value:
        return "Present"
    return _year(value) or "Present"


def _as_bullets(description: str) -> list[str]:
    if not description:
        return []
    lines = []
    for raw in description.splitlines():
        cleaned = re.sub(r"^[\s\-•*\u2022]+", "", raw).strip()
        if cleaned:
            lines.append(cleaned)
    if len(lines) > 1:
        return lines
    return [description.strip()]


def _linkedin_error_message(response: httpx.Response, fallback: str) -> str:
    try:
        body = response.json()
    except ValueError:
        return fallback
    if isinstance(body, dict):
        for key in ("error_description", "message", "error"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return fallback
