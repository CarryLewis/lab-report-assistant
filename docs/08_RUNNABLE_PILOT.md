# Local Runnable Pilot

The runnable app is at `/pilot.html`; `/` retains the earlier interactive prototype.
It uses browser HTML/CSS/JavaScript, a Python HTTP service and SQLite. It has no
frontend build step. Optional certifi supplies a certificate bundle for external APIs.

## Components

- `pilot.html`, `pilot.css`, `pilot.js`: report list, assignment setup, rubric preview,
  model settings and the linked three-column review workspace.
- `pilot_backend.py`: DOCX extraction, rubric validation, report snapshots, revision
  storage, API-key handling, model requests and evidence validation.
- `server.py`: local-only HTTP endpoints and an allowlist for public assets, while
  retaining the scholarly-search endpoints used by the earlier prototype.
- `.labwise/pilot.sqlite3`: report text, assignments, rubric snapshots, instructor
  drafts, scores and historical versions; excluded from source distribution.
- `examples/pilot-rubric.json`: importable rubric for a fictional lab-report demo.

## Data Flow

Create assignment and confirm rubric preview → upload a DOCX → extract paragraph
IDs → run structural/example or DeepSeek analysis → review numbered suggestions
with source/map links → edit feedback, notes and scores → save draft → explicitly
confirm → export student feedback without private instructor notes.

JSON rubric import accepts `maximum_points` or `weight` for each criterion and
normalizes it to criterion points. It does not infer missing weights or silently
rescale an institutional rubric. Rubric changes create a new assignment record;
existing reports retain their original assignment snapshot.

Each save stores the previous report as a revision. Restore creates a new draft
revision and revokes confirmation. Stale clients cannot overwrite newer revisions.
Reanalysis preserves the previous version but resets current reviews, scores and
final feedback. Sample analysis generates feedback only for the built-in fictional
sample with its matching built-in rubric; real reports get structural extraction
until the instructor chooses a configured model.

## API Contract

All endpoints use `/api/pilot/`. Mutations require same-origin JSON requests and
local Host headers. The local app has no user accounts or institutional permissions.

- `GET bootstrap`: saved assignments, report summaries and non-secret settings.
- `POST assignments`: validate and save assignment instructions and a rubric.
- `POST reports`: parse base64 DOCX data or create a fictional sample.
- `GET reports/{id}`: load parsed text, rubric snapshot and current draft.
- `POST reports/{id}/analyze`: generate and validate an analysis.
- `POST reports/{id}/save` and `/confirm`: save instructor actions and scores.
- `GET reports/{id}/revisions` and `POST reports/{id}/restore`: inspect/restore versions.
- `GET reports/{id}/export`: export only instructor-confirmed feedback.
- `POST settings`: save model selection; keep the API key only in process memory.
- `POST connection`: check DeepSeek authentication using its models endpoint.

Analysis output requires a summary, outline, claims and findings. Each finding must
reference an existing rubric criterion and existing paragraph IDs, and its exact
quote must occur in one of those source paragraphs. Invalid/truncated responses
produce an explicit error, without fabricating substitute findings. The model
never supplies the instructor's formal scores.

## Validation and Limits

Run `python3 -m unittest discover -s tests -p 'test_*.py'`. Tests cover parsing,
review/export gates, persistence, version restoration, rubric validation and evidence
validation. Browser checks cover fictional sample analysis, instructor acceptance,
manual scores and confirmation.

Live DeepSeek access requires a valid key and reachable service; it cannot be fully
verified without credentials. Docker files are provided but require local Docker
installation. This is a local single-instructor pilot, not an authenticated shared
school deployment. DOCX images, equations, OCR and original layout rendering,
student delivery, and Turnitin integration remain outside the runnable scope.
