"""Outreach Draft Agent.

Drafts a short cold email grounded in the profile and that job's Fit Scorecard.
Sending is a separate, explicitly approved call — nothing leaves on its own.
"""

from __future__ import annotations

import re

from app.schemas.candidate import Candidate
from app.schemas.job import Job
from app.schemas.outreach import OutreachDraft


def build_draft(
    candidate: Candidate,
    job: Job | None,
    recipient_email: str,
    recipient_name: str | None = None,
    extra_context: str | None = None,
) -> OutreachDraft:
    greeting = f"Hi {recipient_name.split()[0]}," if recipient_name else "Hi there,"
    name = candidate.full_name or "A Matchr candidate"

    grounded_facts: list[str] = []
    current = candidate.experience[0] if candidate.experience else None
    if current:
        grounded_facts.append(f"{current.title} at {current.company}")

    proof = _pick_proof(candidate, job)
    if proof:
        grounded_facts.append(proof)

    if job is None:
        subject = f"{candidate.target_title or 'Engineer'} reaching out"
        body = (
            f"{greeting}\n\n"
            f"I am {name}"
            + (f", currently a {current.title} at {current.company}" if current else "")
            + ".\n\n"
            + (f"{proof}\n\n" if proof else "")
            + "I am exploring roles where that work is the core problem rather than a side "
            "concern. If your team is hiring, I would value fifteen minutes to hear what you "
            "are building.\n\n"
            + (f"{extra_context}\n\n" if extra_context else "")
            + f"Thank you,\n{name}"
        )
        return OutreachDraft(
            subject=subject,
            body=body,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            grounded_facts=grounded_facts,
        )

    matched = job.scorecard.matching_skills if job.scorecard else []
    if matched:
        grounded_facts.append(f"Overlap with the role: {', '.join(matched[:3])}")
    angle = ", ".join(matched[:2]) if matched else "the core of the role"

    subject = f"{job.title} at {job.company} — {candidate.full_name or 'quick note'}"
    body = (
        f"{greeting}\n\n"
        f"I am {name}"
        + (f", a {current.title} at {current.company}" if current else "")
        + f". I saw the {job.title} opening and it lines up closely with what I do day to day, "
        f"particularly {angle}.\n\n"
        + (f"One concrete data point: {proof}\n\n" if proof else "")
        + f"I am not mass-applying — {job.company} is one of a handful of teams I am targeting "
        f"because the problem matches my actual track record. Would you be open to a short "
        f"conversation, or could you point me to whoever owns this req?\n\n"
        + (f"{extra_context}\n\n" if extra_context else "")
        + f"Thank you for your time,\n{name}"
    )

    return OutreachDraft(
        subject=subject,
        body=body,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        job_id=job.id,
        grounded_facts=grounded_facts,
    )


def _pick_proof(candidate: Candidate, job: Job | None) -> str | None:
    """The candidate's own strongest relevant bullet, verbatim."""
    achievements = candidate.achievements
    if not achievements:
        return None

    relevant = set(job.scorecard.matching_skills) if job and job.scorecard else set()

    def rank(bullet: str) -> int:
        from app.services.matching import extract_skills

        overlap = len(set(extract_skills(bullet)) & relevant)
        return overlap * 2 + (1 if re.search(r"\d", bullet) else 0)

    best = max(achievements, key=rank)
    return best if rank(best) > 0 else None
