"""Backend ingest must honor the requested count and keep AI ranking order."""

from app.schemas.candidate import Candidate, Experience
from app.services.store import Store


def _grounded() -> Candidate:
    return Candidate(
        id="cand-1",
        grounded=True,
        target_title="Software Engineer",
        skills=["Python", "AWS"],
        summary="Backend engineer building Python services.",
        experience=[
            Experience(
                title="Software Engineer",
                company="Acme",
                bullets=["Shipped Python APIs on AWS."],
            )
        ],
    )


def _match(job_id: str, title: str, semantic: float, rank: int, description: str = "") -> dict:
    return {
        "id": job_id,
        "title": title,
        "company": "Acme",
        "description": description or title,
        "similarity": semantic,
        "semantic_score": semantic,
        "ranking_score": int(round(semantic * 100)),
        "rank": rank,
    }


def test_ingest_returns_exactly_the_requested_limit():
    store = Store()
    store.set_candidate(_grounded())
    matches = [
        _match(f"job-{index}", "Software Engineer", 0.9 - index * 0.01, index)
        for index in range(1, 21)
    ]
    jobs = store.ingest_and_score_live_jobs(matches, limit=10)
    assert len(jobs) == 10
    assert [job.rank for job in jobs] == list(range(1, 11))


def test_ingest_preserves_semantic_order_not_lexical_percent():
    store = Store()
    store.set_candidate(_grounded())
    # First job is a weak lexical fit but the AI ranked it #1.
    matches = [
        _match("ai-first", "Marketing Coordinator", 0.92, 1, "SEO content calendar"),
        _match("lexical-first", "Software Engineer", 0.41, 2, "Python AWS Kubernetes PostgreSQL"),
        _match("mid", "Data Analyst", 0.30, 3, "Spreadsheets"),
    ]
    jobs = store.ingest_and_score_live_jobs(matches, limit=2)
    assert [job.id for job in jobs] == ["ai-first", "lexical-first"]
    assert jobs[0].scorecard is not None
    assert jobs[0].scorecard.semantic_score == 0.92
    assert jobs[0].scorecard.ranking_score == 92


def test_ingest_attaches_ranking_fields_on_scorecard():
    store = Store()
    store.set_candidate(_grounded())
    jobs = store.ingest_and_score_live_jobs(
        [_match("job-1", "Software Engineer", 0.81, 1, "Python AWS")],
        limit=10,
    )
    assert len(jobs) == 1
    assert jobs[0].rank == 1
    assert jobs[0].scorecard.semantic_score == 0.81
    assert jobs[0].scorecard.ranking_score == 81
    assert jobs[0].scorecard.match_percent >= 30
