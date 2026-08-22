"""Semantic matching engine.

The MVP scores locally instead of calling an embedding API so the product runs
with zero keys. Similarity is real (IDF-weighted cosine over the live corpus),
just computed on lexical vectors rather than neural ones. `CorpusIndex.vector`
is the single seam to swap in `text-embedding-3-small` later.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from app.data.skills import SKILL_ALIASES

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.]*")

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have",
    "how", "in", "into", "is", "it", "its", "of", "on", "or", "our", "that", "the", "their",
    "them", "then", "these", "this", "to", "we", "will", "with", "you", "your", "across",
    "not", "who", "what", "when", "where", "while", "role", "team", "teams", "work",
    "working", "job", "years", "year", "experience", "including", "etc", "per", "day",
}

# Precompiled per canonical skill so extraction is a single pass per alias.
_ALIAS_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    skill: [re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])") for alias in aliases]
    for skill, aliases in SKILL_ALIASES.items()
}


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 1
    ]


def extract_skills(text: str) -> list[str]:
    """Resolve free text into canonical skill names, preserving taxonomy order."""
    lowered = text.lower()
    found: list[str] = []
    for skill, patterns in _ALIAS_PATTERNS.items():
        if any(pattern.search(lowered) for pattern in patterns):
            found.append(skill)
    return found


def skill_emphasis(text: str) -> dict[str, int]:
    """How many times each skill is mentioned — a proxy for how much it matters."""
    lowered = text.lower()
    counts: dict[str, int] = {}
    for skill, patterns in _ALIAS_PATTERNS.items():
        total = sum(len(pattern.findall(lowered)) for pattern in patterns)
        if total:
            counts[skill] = total
    return counts


class CorpusIndex:
    """IDF-weighted bag-of-words index over a document corpus."""

    def __init__(self, documents: list[str]) -> None:
        self._doc_count = max(len(documents), 1)
        document_frequency: Counter[str] = Counter()
        for document in documents:
            document_frequency.update(set(tokenize(document)))
        self._idf = {
            term: math.log((self._doc_count + 1) / (freq + 1)) + 1.0
            for term, freq in document_frequency.items()
        }

    def _idf_for(self, term: str) -> float:
        # Unseen terms are treated as maximally rare.
        return self._idf.get(term, math.log(self._doc_count + 1) + 1.0)

    def vector(self, text: str) -> dict[str, float]:
        counts = Counter(tokenize(text))
        if not counts:
            return {}
        max_count = max(counts.values())
        weights = {
            term: (0.5 + 0.5 * count / max_count) * self._idf_for(term)
            for term, count in counts.items()
        }
        norm = math.sqrt(sum(weight * weight for weight in weights.values()))
        if norm == 0:
            return {}
        return {term: weight / norm for term, weight in weights.items()}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(term, 0.0) for term, weight in left.items())


def title_affinity(target_title: str | None, job_title: str) -> float:
    """Token overlap between the stated goal title and the posting title."""
    if not target_title:
        return 0.5
    target_tokens = set(tokenize(target_title))
    job_tokens = set(tokenize(job_title))
    if not target_tokens or not job_tokens:
        return 0.5
    overlap = len(target_tokens & job_tokens)
    return overlap / len(target_tokens)


@dataclass
class MatchResult:
    match_percent: int
    similarity: float
    matching_skills: list[str]
    missing_tech: list[str]
    key_angle: str


# Lexical cosine over job-length documents lands in roughly 0.03–0.15, so it is
# rescaled into a usable 0–1 band before blending.
_SIMILARITY_SCALE = 5.0

# A posting listing a technology is not the same as requiring it, so unmatched
# emphasis is discounted rather than counted against the candidate one-for-one.
_MISS_PENALTY = 0.6


def _coverage(matched_emphasis: float, missing_emphasis: float) -> float:
    denominator = matched_emphasis + _MISS_PENALTY * missing_emphasis
    return matched_emphasis / denominator if denominator else 0.0


def _blend(skill_coverage: float, similarity: float, affinity: float) -> int:
    """Weighted blend, then a mild curve so realistic fits land in the 60–95 band."""
    raw = (
        0.52 * skill_coverage
        + 0.33 * min(similarity * _SIMILARITY_SCALE, 1.0)
        + 0.15 * affinity
    )
    curved = raw**0.75
    return max(30, min(97, round(curved * 100)))


def _build_key_angle(
    job_title: str,
    company: str,
    matching_skills: list[str],
    missing_tech: list[str],
    evidence: str | None,
) -> str:
    """Templated but grounded: only names skills the profile actually contains."""
    if not matching_skills:
        return (
            f"Thin overlap with {company}. Only pursue this one if you are deliberately "
            f"pivoting toward {job_title.lower()} work."
        )

    lead = ", ".join(matching_skills[:3])
    angle = f"Lead with your {lead} depth — that is the overlap {company} is screening for."
    if evidence:
        angle += f" Put this line first: {evidence}"
    if missing_tech:
        gap = missing_tech[0]
        angle += (
            f" Do not claim {gap}; instead frame the closest adjacent work you have "
            f"actually done."
        )
    return angle


def _pick_evidence(achievements: list[str], matching_skills: list[str]) -> str | None:
    """Find the candidate's own strongest bullet mentioning a matched skill.

    Never fabricates: returns an existing bullet verbatim or nothing at all.
    """
    if not achievements:
        return None
    priority = matching_skills[:4]
    scored: list[tuple[int, str]] = []
    for bullet in achievements:
        bullet_skills = set(extract_skills(bullet))
        overlap = len(bullet_skills & set(priority))
        has_metric = bool(re.search(r"\d", bullet))
        scored.append((overlap * 2 + (1 if has_metric else 0), bullet))
    best_score, best_bullet = max(scored, key=lambda item: item[0])
    return best_bullet if best_score > 0 else None


def score_job(
    *,
    profile_text: str,
    profile_skills: list[str],
    target_title: str | None,
    achievements: list[str],
    job_title: str,
    job_company: str,
    job_description: str,
    index: CorpusIndex,
) -> MatchResult:
    job_text = f"{job_title} {job_company} {job_description}"
    emphasis = skill_emphasis(job_text)
    job_skills = list(emphasis.keys())

    owned = set(profile_skills)
    matching_skills = sorted(
        (skill for skill in job_skills if skill in owned),
        key=lambda skill: -emphasis[skill],
    )
    missing_tech = sorted(
        (skill for skill in job_skills if skill not in owned),
        key=lambda skill: -emphasis[skill],
    )

    matched_emphasis = sum(emphasis[skill] for skill in matching_skills)
    missing_emphasis = sum(emphasis[skill] for skill in missing_tech)
    skill_coverage = _coverage(matched_emphasis, missing_emphasis)

    similarity = cosine(index.vector(profile_text), index.vector(job_text))
    affinity = title_affinity(target_title, job_title)

    return MatchResult(
        match_percent=_blend(skill_coverage, similarity, affinity),
        similarity=round(similarity, 4),
        matching_skills=matching_skills[:8],
        missing_tech=missing_tech[:6],
        key_angle=_build_key_angle(
            job_title,
            job_company,
            matching_skills,
            missing_tech,
            _pick_evidence(achievements, matching_skills),
        ),
    )


def score_event(
    *,
    profile_text: str,
    profile_skills: list[str],
    growth_skills: list[str],
    target_title: str | None,
    location: str | None,
    event_name: str,
    event_description: str,
    event_location: str | None,
    event_format: str,
    attendee_profile: str | None,
    index: CorpusIndex,
) -> tuple[int, str, list[str]]:
    """Rank an event against the profile, goals, and growth-plan skills.

    Growth skills are weighted above owned skills: the point of an event is to
    reach the next role, not to revisit what the candidate already knows.
    """
    event_text = f"{event_name} {event_description} {attendee_profile or ''}"
    event_skills = set(extract_skills(event_text))

    owned_hits = sorted(event_skills & set(profile_skills))
    growth_hits = sorted(event_skills & set(growth_skills))

    denominator = len(event_skills) or 1
    coverage = (len(growth_hits) * 1.5 + len(owned_hits)) / (denominator + 1.5)
    similarity = cosine(index.vector(f"{profile_text} {' '.join(growth_skills)}"), index.vector(event_text))

    proximity = 0.5
    if event_format in {"virtual", "hybrid"}:
        proximity = 1.0
    elif location and event_location:
        candidate_city = location.split(",")[0].strip().lower()
        event_city = event_location.split(",")[0].strip().lower()
        proximity = 1.0 if candidate_city and candidate_city == event_city else 0.35

    raw = (
        0.45 * min(coverage, 1.0)
        + 0.35 * min(similarity * _SIMILARITY_SCALE, 1.0)
        + 0.20 * proximity
    )
    match_percent = max(30, min(96, round((raw**0.8) * 100)))

    why = _build_event_reason(
        event_name, growth_hits, owned_hits, event_format, event_location, target_title
    )
    return match_percent, why, growth_hits or owned_hits


def _build_event_reason(
    event_name: str,
    growth_hits: list[str],
    owned_hits: list[str],
    event_format: str,
    event_location: str | None,
    target_title: str | None,
) -> str:
    goal = target_title or "your target role"
    if growth_hits:
        skills = ", ".join(growth_hits[:3])
        reason = f"Covers {skills} — the exact gaps standing between you and {goal}."
    elif owned_hits:
        skills = ", ".join(owned_hits[:3])
        reason = f"The room is working in {skills}, so you can contribute rather than just listen."
    else:
        reason = f"Adjacent to {goal}; useful for breadth, not for closing a specific gap."

    if event_format == "virtual":
        reason += " Virtual, so no travel cost to test the fit."
    elif event_location:
        reason += f" In {event_location}."
    return reason
