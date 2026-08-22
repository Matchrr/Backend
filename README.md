# Matchr Backend

FastAPI service behind the Matchr dashboard: profile grounding, semantic job and event
matching, skill-gap growth planning, dossier generation, and outreach drafting.

## Run

```bash
npm run dev
```

Creates the virtualenv, installs dependencies, copies `.env` if needed, then starts the API on
port 4000. Interactive docs: http://localhost:4000/docs

**No API keys are required.** This build scores locally against a seeded corpus so the whole
product runs offline.

## How matching works in this build

The spec calls for OpenAI embeddings in Supabase `pgvector`. That is not wired up yet, so
similarity is computed locally and the numbers are still real:

- `app/services/matching.py` builds an IDF-weighted vector over the live corpus and scores
  cosine similarity between the profile and each posting.
- A Fit Scorecard blends three signals: emphasis-weighted skill coverage (52%), corpus
  similarity (33%), and target-title affinity (15%). Technologies a posting merely mentions are
  discounted rather than counted as hard disqualifiers.
- `CorpusIndex.vector` is the seam. Swapping in `text-embedding-3-small` means replacing that
  one method, not the callers.

Skills are resolved through a canonical taxonomy in `app/data/skills.py`, so "k8s", "EKS", and
"Kubernetes" collapse to one skill.

## The grounding guardrail

`app/services/dossier.py` may only reorder, select, and restructure bullets the candidate
already wrote. After generating, it re-reads its own output and rejects any technical claim
absent from the profile — see `verify_grounding`. Sentences that explicitly disclaim experience
("I have not shipped Kafka in production") are excluded, since naming a gap is the opposite of
inventing one.

## State

`app/services/store.py` holds a single candidate in memory, standing in for Supabase. Two
consequences worth knowing:

- State resets whenever the reloader restarts the process, so you re-ground after editing code.
- It is single-candidate by design. Multi-tenancy arrives with real persistence.

`supabase/migrations/001_init.sql` has the target schema for when it does.

Every mutation also appends to an activity log (`Store._log`), which is what the dashboard
timeline reads. Adding a new user-visible action means logging it there, not adding a table.

## The overview aggregate

`GET /api/overview` is the dashboard's single read. It derives the pipeline funnel, the fit
curve, the score distribution, profile completeness, the activity feed, and a `next_action`
server-side, so the client never fans out across five endpoints to re-derive the same numbers.

`next_action` is the highest-leverage thing to do given current state — ground the profile, set
a target, pick targets, build dossiers, send outreach, then work the growth plan. The sidebar
card and the dashboard's primary button both render it, so there is one definition of "what
now" rather than one per surface.

## Routes

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/health` | Liveness |
| GET | `/api/overview` | Everything the dashboard renders, in one pass |
| GET | `/api/overview/activity` | Recent engine events |
| GET | `/api/candidates/me` | Ground Truth Profile |
| PATCH | `/api/candidates/me` | Set target title / location |
| POST | `/api/candidates/linkedin` | Ground from LinkedIn (simulated OAuth) |
| POST | `/api/candidates/resume` | Ground from an uploaded PDF or text resume |
| POST | `/api/candidates/reset` | Clear all state |
| GET | `/api/jobs/matches` | Ranked matches with Fit Scorecards |
| GET | `/api/jobs/{job_id}` | Single scored job |
| POST | `/api/jobs/sync` | Re-harvest listings (seed corpus for now) |
| GET/POST | `/api/applications` | List or target a role (capped at 5) |
| DELETE | `/api/applications/{job_id}` | Drop a target |
| POST | `/api/dossier/{job_id}` | Generate a tailored dossier |
| GET | `/api/growth/plan` | Skill-gap plan with resource packs |
| GET | `/api/events/matches` | Ranked networking events |
| POST | `/api/events/{event_id}/save` | Save or unsave an event |
| POST | `/api/outreach/draft` | Grounded cold-email draft |
| POST | `/api/outreach/send` | Record a send; rejects `approved: false` |
| GET | `/api/outreach/threads` | Sent history |
| GET | `/api/integrations` | LinkedIn / Gmail status |

## Not yet wired

SerpApi harvesting, Supabase persistence, Nutrient PDF export, Kong gateway routing, and real
LinkedIn/Gmail OAuth. Config slots for all of them already exist in `app/core/config.py`, and
the `ai-service` repo holds the agent scaffolding this service will eventually delegate to.
