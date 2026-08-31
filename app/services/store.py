"""In-memory application state for the MVP.

A single live candidate in RAM, with the Ground Truth Profile persisted per
authenticated user (see profile_vault) so login restores LinkedIn/resume
grounding. Job corpus stays shared. Routes keep talking to this class.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

from app.data.seed import EVENT_SEED, JOB_SEED
from app.schemas.application import Application
from app.schemas.candidate import Candidate
from app.schemas.dossier import Dossier
from app.schemas.event import NetworkingEvent
from app.schemas.growth import GrowthPlan
from app.schemas.job import FitScorecard, Job
from app.schemas.outreach import OutreachThread
from app.schemas.overview import (
    ActivityEntry,
    MatchPoint,
    NextAction,
    Overview,
    PipelineStage,
    ScoreBand,
)
from app.services import dossier as dossier_service
from app.services import growth as growth_service
from app.services import profile_vault
from app.services.grounding import CANDIDATE_ID
from app.services.matching import CorpusIndex, extract_skills, score_event, score_job

logger = logging.getLogger(__name__)

MAX_TARGETS = 5
STRONG_MATCH = 75
ACTIVITY_LIMIT = 40

# Outreach has no natural ceiling, so the meter is scaled against a deliberately
# small target that matches the product's quality-over-quantity stance.
OUTREACH_GOAL = 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.candidate = Candidate(id=CANDIDATE_ID)
            self._jobs: dict[str, dict] = {job["id"]: dict(job) for job in JOB_SEED}
            self._events: dict[str, dict] = {event["id"]: dict(event) for event in EVENT_SEED}
            self._targeted: list[str] = []
            self._saved_events: set[str] = set()
            self._applications: dict[str, Application] = {}
            self._dossiers: dict[str, Dossier] = {}
            self._threads: list[OutreachThread] = []
            self._activity: list[ActivityEntry] = []
            self._last_sync: str | None = None
            self._sequence = 0
            self._linkedin_tokens: dict[str, object] | None = None
            self._live_active = False
            self._match_filters: dict[str, object] = {}
            self._profile_revision_id: int | None = None
            self._rebuild_index()

    # ----- activity --------------------------------------------------------

    def _log(self, kind: str, title: str, detail: str | None = None, tone: str = "neutral") -> None:
        """Records a user-visible event for the dashboard feed.

        Called from inside methods that already hold the lock.
        """
        self._sequence += 1
        self._activity.insert(
            0,
            ActivityEntry(
                id=f"act_{self._sequence}",
                kind=kind,
                title=title,
                detail=detail,
                tone=tone,
                at=_now(),
            ),
        )
        del self._activity[ACTIVITY_LIMIT:]

    def activity(self, limit: int = 8) -> list[ActivityEntry]:
        with self._lock:
            return self._activity[:limit]

    def _rebuild_index(self) -> None:
        documents = [
            f"{job['title']} {job['company']} {job['description']}" for job in self._jobs.values()
        ]
        documents += [
            f"{event['name']} {event['description']} {event.get('attendee_profile', '')}"
            for event in self._events.values()
        ]
        self._index = CorpusIndex(documents)

    # ----- candidate -------------------------------------------------------

    def set_candidate(self, candidate: Candidate) -> Candidate:
        with self._lock:
            self._stamp_owner_locked(candidate)
            self.candidate = candidate
            self._dossiers.clear()
            if candidate.grounded:
                self._profile_revision_id = int(time.time() * 1000)
                sources = ", ".join(candidate.grounding_sources) or "unknown source"
                self._log(
                    "grounded",
                    "Ground Truth Profile updated",
                    f"{len(candidate.skills)} verified skills via {sources}",
                    tone="positive",
                )
            else:
                self._log(
                    "grounded",
                    "LinkedIn identity imported",
                    candidate.full_name or candidate.email,
                    tone="info",
                )
            self._persist_locked()
            return self.candidate

    def set_linkedin_tokens(self, tokens: dict[str, object]) -> None:
        with self._lock:
            self._linkedin_tokens = {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in"),
                "scope": tokens.get("scope"),
            }
            self._persist_locked()

    def linkedin_access_token(self) -> str | None:
        with self._lock:
            if not self._linkedin_tokens:
                return None
            token = self._linkedin_tokens.get("access_token")
            return token if isinstance(token, str) and token else None

    def bind_identity(
        self,
        user_id: str,
        email: str | None = None,
        full_name: str | None = None,
    ) -> Candidate:
        """Attach the live candidate record to a Xano user and restore their profile.

        The job corpus stays shared. Switching accounts flushes RAM (after saving
        the previous user) and loads the incoming user's last grounded profile.
        """
        with self._lock:
            current_id = self.candidate.id
            if current_id not in {CANDIDATE_ID, user_id}:
                self._persist_locked()
                self.reset()
                self._hydrate_locked(user_id)
            elif current_id == CANDIDATE_ID:
                self._hydrate_locked(user_id)
            self.candidate.id = user_id
            if email:
                self.candidate.email = email
            if full_name and not self.candidate.full_name:
                self.candidate.full_name = full_name
            return self.candidate

    def reset_profile(self) -> Candidate:
        """Wipe this account's Ground Truth Profile (RAM + durable copy)."""
        with self._lock:
            user_id = self.candidate.id
            email = self.candidate.email
            profile_vault.delete(user_id)
            self.reset()
            if profile_vault.is_persisted_user(user_id):
                self.candidate.id = user_id
                self.candidate.email = email
            return self.candidate

    def update_candidate(self, **fields: object) -> Candidate:
        with self._lock:
            previous_target = self.candidate.target_title
            for key, value in fields.items():
                if value is not None and hasattr(self.candidate, key):
                    if key == "location" and isinstance(value, str):
                        from app.services.career_parse import city_only_location

                        value = city_only_location(value) or value
                    setattr(self.candidate, key, value)
            self._dossiers.clear()
            if self.candidate.target_title and self.candidate.target_title != previous_target:
                self._log(
                    "goal",
                    f"Target role set to {self.candidate.target_title}",
                    "Matches, growth plan, and events re-ranked against the new goal",
                    tone="brand",
                )
            self._persist_locked()
            return self.candidate

    def _stamp_owner_locked(self, candidate: Candidate) -> None:
        owner_id = self.candidate.id
        if not profile_vault.is_persisted_user(owner_id):
            return
        candidate.id = owner_id
        if not candidate.email:
            candidate.email = self.candidate.email

    def _hydrate_locked(self, user_id: str) -> None:
        saved = profile_vault.load(user_id)
        if saved is None:
            return
        self.candidate = saved.candidate
        self._linkedin_tokens = saved.linkedin_tokens
        self._profile_revision_id = saved.profile_revision_id

    def _persist_locked(self) -> None:
        try:
            profile_vault.save(
                self.candidate,
                linkedin_tokens=self._linkedin_tokens,
                profile_revision_id=self._profile_revision_id,
            )
        except Exception:
            logger.exception("Could not persist profile for user %s", self.candidate.id)

    # ----- jobs ------------------------------------------------------------

    def _score(self, record: dict) -> Job:
        job = Job(
            id=record["id"],
            title=record["title"],
            company=record["company"],
            location=record.get("location"),
            source=record.get("source"),
            posted_at=record.get("posted_at"),
            salary=record.get("salary"),
            apply_url=record.get("apply_url"),
            description=record.get("description"),
            targeted=record["id"] in self._targeted,
        )
        if not self.candidate.grounded:
            return job

        result = score_job(
            profile_text=self.candidate.profile_text,
            profile_skills=self.candidate.skills,
            target_title=self.candidate.target_title,
            achievements=self.candidate.achievements,
            job_title=job.title,
            job_company=job.company,
            job_description=job.description or "",
            index=self._index,
            embedding_similarity=record.get("similarity") if "similarity" in record else None,
        )
        job.scorecard = FitScorecard(
            match_percent=result.match_percent,
            similarity=result.similarity,
            matching_skills=result.matching_skills,
            missing_tech=result.missing_tech,
            key_angle=result.key_angle,
        )
        return job

    def job_matches(self, limit: int = 10) -> list[Job]:
        with self._lock:
            records = [
                record
                for record in self._jobs.values()
                if not self._live_active or record.get("_origin") == "live"
            ]
            jobs = [self._score(record) for record in records]
            if self.candidate.grounded:
                jobs.sort(key=lambda job: -(job.scorecard.match_percent if job.scorecard else 0))
            return jobs[:limit]

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            record = self._jobs.get(job_id)
            return self._score(record) if record else None

    def sync_jobs(self) -> dict[str, object]:
        """Seed-corpus fallback when live harvest is unavailable."""
        with self._lock:
            self._live_active = False
            self._last_sync = _now()
            self._rebuild_index()
            self._log(
                "sync",
                f"Re-scored {len(self._jobs)} live roles",
                "Corpus refreshed and every Fit Scorecard recomputed",
                tone="info",
            )
            return {"synced": len(self._jobs), "at": self._last_sync, "source": "seed_corpus"}

    @property
    def last_sync(self) -> str | None:
        return self._last_sync

    @property
    def match_filters(self) -> dict[str, object]:
        return dict(self._match_filters)

    def set_match_filters(self, **fields: object) -> None:
        with self._lock:
            for key, value in fields.items():
                if value is None:
                    self._match_filters.pop(key, None)
                else:
                    self._match_filters[key] = value

    def mark_live_sync(self, stats: dict[str, object]) -> dict[str, object]:
        with self._lock:
            self._live_active = True
            self._last_sync = str(stats.get("at") or _now())
            synced = int(stats.get("synced") or 0)
            harvested = int(stats.get("harvested_queries") or 0)
            cached = int(stats.get("cached_queries") or 0)
            warning = stats.get("warning")
            detail = f"{harvested} live searches · {cached} cached"
            if warning:
                detail = f"{detail} · {warning}"
            self._log(
                "sync",
                f"Harvested {synced} live roles" if synced else "Refreshed live job catalog",
                detail,
                tone="info",
            )
            payload = dict(stats)
            payload["at"] = self._last_sync
            payload["source"] = "xano"
            return payload

    def ingest_and_score_live_jobs(self, matches: list[dict], limit: int = 10) -> list[Job]:
        with self._lock:
            records: list[dict] = []
            for item in matches:
                job_id = str(item.get("id") or item.get("external_id") or "").strip()
                title = str(item.get("title") or "").strip()
                company = str(item.get("company") or "").strip()
                if not job_id or not title:
                    continue
                record = {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": item.get("location"),
                    "source": item.get("source"),
                    "posted_at": item.get("posted_at"),
                    "salary": item.get("salary"),
                    "apply_url": item.get("apply_url"),
                    "description": item.get("description"),
                    "similarity": item.get("similarity"),
                    "xano_id": item.get("xano_id"),
                    "_origin": "live",
                }
                self._jobs[job_id] = record
                records.append(record)
            self._live_active = True
            self._rebuild_index()
            jobs = [self._score(record) for record in records]
            jobs.sort(key=lambda job: -(job.scorecard.match_percent if job.scorecard else 0))
            return jobs[:limit]

    # ----- targeting / applications ---------------------------------------

    def target_job(self, job_id: str) -> Application:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise KeyError(job_id)
            if job_id not in self._targeted:
                if len(self._targeted) >= MAX_TARGETS:
                    raise ValueError(
                        f"Matchr caps targets at {MAX_TARGETS}. Drop one before adding another."
                    )
                self._targeted.append(job_id)
                self._log(
                    "targeted",
                    f"Targeted {record['title']}",
                    f"{record['company']} — {len(self._targeted)} of {MAX_TARGETS} slots used",
                    tone="brand",
                )

            application = Application(
                id=f"app_{job_id}",
                candidate_id=self.candidate.id,
                job_id=job_id,
                job_title=record["title"],
                company=record["company"],
                status="targeted",
                created_at=_now(),
            )
            self._applications[job_id] = application
            return application

    def untarget_job(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._targeted:
                self._targeted.remove(job_id)
                record = self._jobs.get(job_id, {})
                self._log(
                    "untargeted",
                    f"Dropped {record.get('title', 'a role')}",
                    f"{len(self._targeted)} of {MAX_TARGETS} slots used",
                )
            self._applications.pop(job_id, None)
            self._dossiers.pop(job_id, None)

    def applications(self) -> list[Application]:
        with self._lock:
            return [self._applications[job_id] for job_id in self._targeted if job_id in self._applications]

    def set_application_status(self, job_id: str, status: str) -> Application | None:
        with self._lock:
            application = self._applications.get(job_id)
            if application:
                application.status = status
            return application

    # ----- growth ----------------------------------------------------------

    def growth_plan(self) -> GrowthPlan:
        with self._lock:
            return growth_service.build_growth_plan(self.candidate, self.job_matches(limit=10))

    # ----- events ----------------------------------------------------------

    def event_matches(self, limit: int = 8) -> list[NetworkingEvent]:
        with self._lock:
            gap_skills = growth_service.gap_skills(self.growth_plan())
            results: list[NetworkingEvent] = []

            for record in self._events.values():
                event = NetworkingEvent(
                    id=record["id"],
                    name=record["name"],
                    organizer=record.get("organizer"),
                    location=record.get("location"),
                    format=record.get("format", "in-person"),
                    starts_at=record.get("starts_at"),
                    url=record.get("url"),
                    description=record.get("description"),
                    attendee_profile=record.get("attendee_profile"),
                    saved=record["id"] in self._saved_events,
                )
                if self.candidate.grounded:
                    percent, why, topics = score_event(
                        profile_text=self.candidate.profile_text,
                        profile_skills=self.candidate.skills,
                        growth_skills=gap_skills,
                        target_title=self.candidate.target_title,
                        location=self.candidate.location,
                        event_name=event.name,
                        event_description=event.description or "",
                        event_location=event.location,
                        event_format=event.format,
                        attendee_profile=event.attendee_profile,
                        index=self._index,
                    )
                    event.match_percent = percent
                    event.why_this_event = why
                    event.topics = topics
                else:
                    event.topics = extract_skills(event.description or "")[:5]
                results.append(event)

            if self.candidate.grounded:
                results.sort(key=lambda event: -(event.match_percent or 0))
            return results[:limit]

    def toggle_saved_event(self, event_id: str, saved: bool) -> None:
        with self._lock:
            if event_id not in self._events:
                raise KeyError(event_id)
            if saved and event_id not in self._saved_events:
                self._saved_events.add(event_id)
                self._log(
                    "event",
                    f"Saved {self._events[event_id]['name']}",
                    self._events[event_id].get("location"),
                    tone="info",
                )
            elif not saved:
                self._saved_events.discard(event_id)

    # ----- dossier ---------------------------------------------------------

    def generate_dossier(self, job_id: str) -> Dossier:
        with self._lock:
            job = self.get_job(job_id)
            if job is None:
                raise KeyError(job_id)
            built = dossier_service.build_dossier(self.candidate, job)
            self._dossiers[job_id] = built
            if job_id in self._applications:
                self._applications[job_id].status = "dossier_ready"
            self._log(
                "dossier",
                f"Dossier built for {job.company}",
                (
                    f"{len(built.tailored_bullets)} bullets tailored · "
                    f"grounding {'passed' if built.grounding.passed else 'failed'}"
                ),
                tone="positive" if built.grounding.passed else "danger",
            )
            return built

    def profile_revision_id(self) -> int | None:
        return self._profile_revision_id

    def job_xano_id(self, job_id: str) -> int | None:
        with self._lock:
            record = self._jobs.get(job_id) or {}
            raw = record.get("xano_id")
            try:
                return int(raw) if raw is not None else None
            except (TypeError, ValueError):
                return None

    def profile_payload(self) -> dict:
        candidate = self.candidate
        return {
            "full_name": candidate.full_name,
            "summary": candidate.summary,
            "skills": list(candidate.skills),
            "experience": [role.model_dump() for role in candidate.experience],
            "volunteering": [role.model_dump() for role in candidate.volunteering],
            "projects": list(candidate.projects),
            "education": list(candidate.education),
            "certifications": list(candidate.certifications),
        }

    def attach_rag_cover_letter(self, job_id: str, rag: dict) -> Dossier | None:
        """Replace the template letter when RAG output still passes grounding."""
        cover_letter = str(rag.get("cover_letter") or "").strip()
        if not cover_letter:
            return None
        with self._lock:
            existing = self._dossiers.get(job_id)
            if existing is None:
                return None
            claims = [bullet.tailored for bullet in existing.tailored_bullets]
            claims += [dossier_service._affirmative_text(cover_letter)]
            claims += [dossier_service._affirmative_text(answer.answer) for answer in existing.ats_answers]
            grounding = dossier_service.verify_grounding(self.candidate, claims)
            if not grounding.passed:
                return existing
            retrieved = rag.get("retrieved_chunk_ids") or []
            chunk_ids = [int(item) for item in retrieved if str(item).isdigit() or isinstance(item, int)]
            cover_letter_id = rag.get("cover_letter_id")
            try:
                stored_id = int(cover_letter_id) if cover_letter_id is not None else None
            except (TypeError, ValueError):
                stored_id = None
            updated = existing.model_copy(
                update={
                    "cover_letter": cover_letter,
                    "grounding": grounding,
                    "generation_source": rag.get("generation_source"),
                    "retrieved_chunk_ids": chunk_ids,
                    "cover_letter_id": stored_id,
                }
            )
            self._dossiers[job_id] = updated
            return updated

    def get_dossier(self, job_id: str) -> Dossier | None:
        with self._lock:
            return self._dossiers.get(job_id)

    # ----- outreach --------------------------------------------------------

    def record_outreach(
        self, recipient_email: str, subject: str, body: str, job_id: str | None
    ) -> OutreachThread:
        with self._lock:
            job = self._jobs.get(job_id) if job_id else None
            thread = OutreachThread(
                id=f"thread_{len(self._threads) + 1}",
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                job_id=job_id,
                job_title=job["title"] if job else None,
                status="sent",
                sent_at=_now(),
            )
            self._threads.append(thread)
            if job_id and job_id in self._applications:
                self._applications[job_id].status = "outreach_sent"
            self._log(
                "outreach",
                f"Emailed {recipient_email}",
                f"Re: {thread.job_title}" if thread.job_title else subject,
                tone="positive",
            )
            return thread

    def threads(self) -> list[OutreachThread]:
        with self._lock:
            return list(reversed(self._threads))

    # ----- overview --------------------------------------------------------

    def _profile_completeness(self) -> int:
        """Weighted checklist of what downstream agents need to do good work."""
        candidate = self.candidate
        checks = (
            (candidate.grounded, 30),
            (bool(candidate.target_title), 20),
            (len(candidate.skills) >= 5, 15),
            (bool(candidate.experience), 15),
            (bool(candidate.location), 10),
            (bool(candidate.education or candidate.certifications), 5),
            (candidate.linkedin_connected, 3),
            (candidate.gmail_connected, 2),
        )
        return sum(weight for passed, weight in checks if passed)

    def _pipeline(self, strong: int) -> list[PipelineStage]:
        scored = len(self._jobs)
        base = max(scored, 1)
        stages = (
            ("scored", "Roles scored", scored, "neutral", "Live corpus ranked against your profile"),
            ("strong", "Strong fits", strong, "brand", f"{STRONG_MATCH}% match or better"),
            (
                "targeted",
                "Targeted",
                len(self._targeted),
                "info",
                f"Capped at {MAX_TARGETS} on purpose",
            ),
            ("dossier", "Dossiers ready", len(self._dossiers), "warning", "Tailored and verified"),
            ("outreach", "Outreach sent", len(self._threads), "positive", "Approved by you"),
        )
        return [
            PipelineStage(
                key=key,
                label=label,
                count=count,
                percent=round(100 * count / base, 1),
                tone=tone,
                hint=hint,
            )
            for key, label, count, tone, hint in stages
        ]

    def _match_curve(self, matches: list[Job]) -> list[MatchPoint]:
        points: list[MatchPoint] = []
        for job in matches:
            if not job.scorecard:
                continue
            matched = len(job.scorecard.matching_skills)
            missing = len(job.scorecard.missing_tech)
            total = matched + missing
            points.append(
                MatchPoint(
                    label=job.company.split(" ")[0][:10],
                    title=job.title,
                    company=job.company,
                    match=job.scorecard.match_percent,
                    coverage=round(100 * matched / total) if total else 100,
                )
            )
        return points

    @staticmethod
    def _score_bands(scores: list[int]) -> list[ScoreBand]:
        bands = (
            ("80%+", "positive", lambda value: value >= 80),
            ("70–79%", "brand", lambda value: 70 <= value < 80),
            ("60–69%", "info", lambda value: 60 <= value < 70),
            ("<60%", "neutral", lambda value: value < 60),
        )
        return [
            ScoreBand(label=label, tone=tone, count=sum(1 for value in scores if test(value)))
            for label, tone, test in bands
        ]

    def _next_action(self, strong: int) -> NextAction:
        """The single highest-leverage thing to do next, given current state."""
        if not self.candidate.grounded:
            if self.candidate.linkedin_connected:
                return NextAction(
                    label="Finish grounding",
                    description=(
                        "LinkedIn shared your identity. Drop a LinkedIn PDF or resume so Matchr "
                        "can score jobs against your actual experience."
                    ),
                    href="/profile?setup=1",
                    cta="Add work history",
                )
            return NextAction(
                label="Ground your profile",
                description=(
                    "Connect LinkedIn or upload a resume. Nothing can rank, tailor, or draft "
                    "until Matchr has verified facts to work from."
                ),
                href="/profile?setup=1",
                cta="Get grounded",
            )
        if not self.candidate.target_title:
            return NextAction(
                label="Set a target role",
                description=(
                    "Your target title is the single biggest lever on match quality — it drives "
                    "ranking, the skill-gap plan, and event compatibility."
                ),
                href="/profile",
                cta="Set target",
            )
        if not self._targeted:
            return NextAction(
                label="Pick your targets",
                description=(
                    f"{strong} role{'s' if strong != 1 else ''} scored at {STRONG_MATCH}% or "
                    f"better. Choose up to {MAX_TARGETS} — the cap is the whole point."
                ),
                href="/jobs",
                cta="Review matches",
            )
        if len(self._dossiers) < len(self._targeted):
            pending = len(self._targeted) - len(self._dossiers)
            noun = "role still needs" if pending == 1 else "roles still need"
            return NextAction(
                label="Build your dossiers",
                description=(
                    f"{pending} targeted {noun} a tailored resume, cover letter, "
                    "and ATS answer set."
                ),
                href="/dossier",
                cta="Generate dossier",
            )
        if not self._threads:
            return NextAction(
                label="Reach a human",
                description=(
                    "Your dossiers are ready. A short, specific email to someone on the team "
                    "beats another submission into the void."
                ),
                href="/outreach",
                cta="Draft outreach",
            )
        return NextAction(
            label="Keep closing gaps",
            description=(
                "Applications are out. Work the growth plan so the next batch of matches "
                "scores higher than this one."
            ),
            href="/growth",
            cta="Open growth plan",
        )

    def overview(self) -> Overview:
        with self._lock:
            matches = self.job_matches(limit=10)
            scores = [job.scorecard.match_percent for job in matches if job.scorecard]
            strong = sum(1 for percent in scores if percent >= STRONG_MATCH)
            recruiters = {thread.recipient_email.lower() for thread in self._threads}

            gaps = 0
            if self.candidate.grounded:
                gaps = len(growth_service.build_growth_plan(self.candidate, matches).skill_gaps)

            return Overview(
                grounded=self.candidate.grounded,
                grounding_sources=self.candidate.grounding_sources,
                target_title=self.candidate.target_title,
                candidate_name=self.candidate.full_name,
                location=self.candidate.location,
                skill_count=len(self.candidate.skills),
                jobs_in_corpus=len(self._jobs),
                top_match_percent=max(scores) if scores else None,
                average_match_percent=round(sum(scores) / len(scores)) if scores else None,
                strong_matches=strong,
                targeted_count=len(self._targeted),
                target_limit=MAX_TARGETS,
                dossiers_ready=len(self._dossiers),
                events_matched=len(self._events),
                events_saved=len(self._saved_events),
                outreach_sent=len(self._threads),
                outreach_goal=OUTREACH_GOAL,
                recruiters_emailed=len(recruiters),
                open_skill_gaps=gaps,
                profile_completeness=self._profile_completeness(),
                last_sync=self._last_sync,
                linkedin_connected=self.candidate.linkedin_connected,
                gmail_connected=self.candidate.gmail_connected,
                pipeline=self._pipeline(strong),
                match_curve=self._match_curve(matches),
                score_bands=self._score_bands(scores),
                activity=self._activity[:8],
                next_action=self._next_action(strong),
            )


store = Store()
