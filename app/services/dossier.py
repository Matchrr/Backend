"""Integrity-checked dossier generation.

The tailoring rule: reorder, select, and restructure bullets the candidate
already wrote. It never introduces a technology the Ground Truth Profile does
not contain, and `verify_grounding` re-checks the output to prove it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.data.skills import SKILL_ALIASES
from app.schemas.candidate import Candidate
from app.schemas.dossier import AtsAnswer, Dossier, GroundingCheck, TailoredBullet
from app.schemas.job import Job
from app.services.matching import extract_skills

MAX_BULLETS = 6

# Trailing outcome clauses get promoted to the front so impact leads.
_OUTCOME_VERBS = {
    "cutting": "Cut",
    "reducing": "Reduced",
    "lowering": "Lowered",
    "saving": "Saved",
    "raising": "Raised",
    "increasing": "Increased",
    "improving": "Improved",
    "boosting": "Boosted",
    "eliminating": "Eliminated",
    "driving": "Drove",
    "enabling": "Enabled",
}
_OUTCOME_RE = re.compile(
    rf"^(?P<lead>.+?),\s+(?P<verb>{'|'.join(_OUTCOME_VERBS)})\s+(?P<outcome>.+?)\.?$",
    re.IGNORECASE,
)


def build_dossier(candidate: Candidate, job: Job) -> Dossier:
    relevant = _relevant_skills(candidate, job)

    bullets = _tailor_bullets(candidate, set(relevant))
    cover_letter = _cover_letter(candidate, job, bullets, relevant)
    ats_answers = _ats_answers(candidate, job, relevant)

    # Only affirmative statements are claims. Naming a gap the candidate does
    # not have ("I have not shipped Kubernetes") is the opposite of a fabrication.
    claims = [bullet.tailored for bullet in bullets]
    claims += [_affirmative_text(cover_letter)]
    claims += [_affirmative_text(answer.answer) for answer in ats_answers]
    grounding = verify_grounding(candidate, claims)

    return Dossier(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        summary=_summary(candidate, job, relevant),
        tailored_bullets=bullets,
        cover_letter=cover_letter,
        ats_answers=ats_answers,
        grounding=grounding,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


_NEGATION_MARKERS = (
    "have not",
    "haven't",
    "not in production",
    "do not have",
    "don't have",
    "would not claim",
    "actively closing",
    "closing that gap",
    "not claim",
)


def _relevant_skills(candidate: Candidate, job: Job) -> list[str]:
    """Skills shared by the profile and posting, ordered by how much the posting stresses them."""
    if job.scorecard and job.scorecard.matching_skills:
        return list(job.scorecard.matching_skills)
    owned = set(candidate.skills)
    return [
        skill
        for skill in extract_skills(f"{job.title} {job.description or ''}")
        if skill in owned
    ]


def _affirmative_text(text: str) -> str:
    """Drop sentences that explicitly disclaim experience before grounding checks."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(
        sentence
        for sentence in sentences
        if not any(marker in sentence.lower() for marker in _NEGATION_MARKERS)
    )


def verify_grounding(candidate: Candidate, generated_texts: list[str]) -> GroundingCheck:
    """Reject any technical claim absent from the Ground Truth Profile."""
    owned = {skill.lower() for skill in candidate.skills}
    source_text = candidate.profile_text.lower()

    rejected: list[str] = []
    checked = 0
    for text in generated_texts:
        for skill in extract_skills(text):
            checked += 1
            if skill.lower() in owned:
                continue
            aliases = [skill.lower(), *(SKILL_ALIASES.get(skill) or [])]
            if any(alias in source_text for alias in aliases):
                continue
            rejected.append(skill)

    unique_rejected = sorted(set(rejected))
    passed = not unique_rejected
    note = (
        f"All {checked} technical claims trace back to your verified history."
        if passed
        else f"Blocked {len(unique_rejected)} unverified claim(s): {', '.join(unique_rejected)}."
    )
    return GroundingCheck(
        passed=passed,
        claims_checked=checked,
        rejected_claims=unique_rejected,
        note=note,
    )


def _tailor_bullets(candidate: Candidate, relevant: set[str]) -> list[TailoredBullet]:
    scored: list[tuple[float, str, list[str]]] = []
    for bullet in candidate.achievements:
        bullet_skills = extract_skills(bullet)
        overlap = [skill for skill in bullet_skills if skill in relevant]
        has_metric = bool(re.search(r"\d", bullet))
        score = len(overlap) * 2 + (1 if has_metric else 0)
        scored.append((score, bullet, overlap))

    scored.sort(key=lambda item: -item[0])

    tailored: list[TailoredBullet] = []
    for _, original, overlap in scored[:MAX_BULLETS]:
        rewritten = _lead_with_outcome(original)
        tailored.append(
            TailoredBullet(
                original=original,
                tailored=rewritten,
                emphasized_skills=overlap,
                changed=rewritten != original,
            )
        )
    return tailored


def _lead_with_outcome(bullet: str) -> str:
    """Promote a trailing result clause to the front. Rearranges only."""
    match = _OUTCOME_RE.match(bullet.strip())
    if not match:
        return bullet
    verb = _OUTCOME_VERBS[match.group("verb").lower()]
    outcome = match.group("outcome").strip().rstrip(".")
    lead = match.group("lead").strip()
    lead = lead[0].lower() + lead[1:] if lead else lead
    return f"{verb} {outcome} — {lead}."


def _summary(candidate: Candidate, job: Job, relevant: list[str]) -> str:
    if not relevant:
        return (
            f"Your profile shares little vocabulary with {job.company}'s posting. "
            "Tailoring cannot manufacture overlap that is not there."
        )
    top = ", ".join(relevant[:4])
    role = candidate.experience[0].title if candidate.experience else "your current role"
    return (
        f"Positioned as a {job.title.lower()} candidate coming from {role}, leading with "
        f"{top}. Bullets were reordered and impact moved to the front — no new claims added."
    )


def _cover_letter(
    candidate: Candidate,
    job: Job,
    bullets: list[TailoredBullet],
    relevant: list[str],
) -> str:
    name = candidate.full_name or "your candidate"
    current = candidate.experience[0] if candidate.experience else None
    current_line = (
        f"I am currently a {current.title} at {current.company}"
        if current
        else "I am currently between roles"
    )
    skills_line = ", ".join(relevant[:3]) if relevant else "the fundamentals"
    evidence = [bullet.tailored for bullet in bullets[:2]]
    evidence_block = "\n".join(f"- {item}" for item in evidence)

    closing_gap = ""
    if job.scorecard and job.scorecard.missing_tech:
        gap = job.scorecard.missing_tech[0]
        closing_gap = (
            f"\n\nI have not shipped {gap} in production. I am working through it now, and I "
            f"would rather tell you that up front than discover it in week one."
        )

    return (
        f"Dear {job.company} Hiring Team,\n\n"
        f"I am applying for the {job.title} role. {current_line}, where my work centers on "
        f"{skills_line} — the same ground your posting describes.\n\n"
        f"Two things from my record that map directly to this role:\n{evidence_block}\n\n"
        f"What draws me to {job.company} specifically is that the problem is infrastructural "
        f"rather than cosmetic: the posting asks for judgment about correctness and scale, "
        f"which is where I have spent my career."
        f"{closing_gap}\n\n"
        f"Thank you for your time.\n\n{name}"
    )


def _ats_answers(candidate: Candidate, job: Job, relevant: list[str]) -> list[AtsAnswer]:
    years = _years_of_experience(candidate)
    top_skill = relevant[0] if relevant else (candidate.skills[0] if candidate.skills else "software")
    strongest = next(
        (bullet for bullet in candidate.achievements if re.search(r"\d", bullet)),
        None,
    )

    answers = [
        AtsAnswer(
            question="What are your salary expectations?",
            answer=(
                f"Your posted range of {job.salary} works for me; I am targeting the upper "
                f"half of it based on {years} years of directly relevant experience, and I am "
                f"open to discussing the full package."
                if job.salary
                else (
                    "I am looking for a package aligned with the market rate for this scope "
                    f"and my {years} years of relevant experience. Happy to work from your "
                    "band once you share it."
                )
            ),
        ),
        AtsAnswer(
            question=f"Why do you want to work at {job.company}?",
            answer=(
                f"The {job.title} role is a direct extension of what I already do. The posting "
                f"emphasizes {top_skill}, which is central to my current work, and the scope "
                f"is larger than what I own today — that combination is what I am looking for."
            ),
        ),
        AtsAnswer(
            question="Tell us about a time you had significant measurable impact.",
            answer=(
                strongest
                or "Add a quantified achievement to your profile and this answer will use it."
            ),
        ),
        AtsAnswer(
            question=f"How many years of experience do you have with {top_skill}?",
            answer=(
                f"{years} years, applied continuously across "
                f"{len(candidate.experience)} role(s) rather than in isolated projects."
            ),
        ),
    ]

    if job.scorecard and job.scorecard.missing_tech:
        gap = job.scorecard.missing_tech[0]
        answers.append(
            AtsAnswer(
                question=f"Do you have experience with {gap}?",
                answer=(
                    f"Not in production. I am actively closing that gap, and the adjacent work "
                    f"I have shipped in {top_skill} transfers most of the underlying reasoning. "
                    f"I would not claim depth I do not have."
                ),
            )
        )
    return answers


def _years_of_experience(candidate: Candidate) -> int:
    years: list[int] = []
    for role in candidate.experience:
        for value in (role.start_date, role.end_date):
            if value and value.isdigit():
                years.append(int(value))
    if not years:
        return len(candidate.experience) or 1
    current_year = datetime.now(timezone.utc).year
    has_present = any(
        (role.end_date or "").lower() in {"present", "current"} for role in candidate.experience
    )
    end = current_year if has_present else max(years)
    return max(1, end - min(years))
