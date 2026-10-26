# Editable Individual Teacher Product

> Superseded for the current UI by [Labwise 1.2](UI_VERSION_1_2.md). Retained as historical design/implementation notes.

Updated 24 October 2026. This document records the implementation of the reduced
V1 workflow. The only application entry remains `/`; `/pilot.html` redirects there.
The previous static page is retained under archive/prototype-2026-10-24 for local
reference and is not exposed as a public application asset.

## Implemented journey

Create/edit an assignment topic and type → import/edit numeric rubric text → save
and pin its version → import a single DOCX/text PDF or a batch of DOCX submissions
→ open an actual saved report in the three-column workspace → edit overview,
map titles, candidate wording, criterion scores, final feedback and private notes
→ save a draft or confirm → export confirmed feedback.

Dashboard counts and lists derive from saved non-sample report records. Reports
can be searched, filtered by confirmation status, renamed, annotated with a student
alias, archived and resumed. Assignments can be copied to a new independent topic,
archived and restored. Settings offers restoration of archived records.

Original extracted source text remains immutable for evidence identity. Importing
a revised file creates another submission; visual Word/PDF page fidelity and
original-file download are not implemented. Source paragraphs are shown with stable
IDs. Map markers and rubric findings share IDs and highlight/locate source evidence
on hover, focus or selection.

## Persistence and version semantics

SQLite stores assignment versions, report snapshots, overview/map-title edits,
suggestion edits, scores, decisions, notes, feedback and reading preferences.
Service keys stay in process memory or the deployment environment, never browser
storage or SQLite. The former browser-only preference UI is replaced by server
persistence. Model names are checked against existing supported options; current
DeepSeek official documentation lists deepseek-flash and deepseek-v4-pro:
https://api-docs.deepseek.com/quick_start/pricing/

Changing a rubric does not rewrite imported report snapshots. Confirmation requires
all rubric scores within bounds, review of every model finding and nonempty final
feedback. Saving subsequent edits invalidates confirmation. Export is server-gated
on confirmation and excludes private notes. Report metadata changes invalidate
confirmation as well. Restore creates an unconfirmed draft and preserves the
previous saved state in history.

Reanalysis retains teacher scores, feedback, notes and edited overview; it replaces
the candidate analysis and resets its review decisions and map-title overrides.
A version snapshot retains prior candidates and decisions. The teacher must review
the new findings and confirm again. An analysis error preserves previous content
and exposes a retry path.

## Available output and settings

Confirmed feedback supports Word, plain text, printable HTML/PDF through browser
printing and a copyable manual-entry Turnitin summary. The export dialog does not
expose internal JSON to the ordinary teacher workflow.

Settings provides teacher display name, source font size/spacing, the existing
DeepSeek model choices, key replacement/clearing and a live connection-check action.
No AI call is made by importing a report or editing criteria. AI analysis requires
an explicit action and notice before sending report text to the service. Without a
key, structure extraction and manual marking remain usable.

## Verification and release limits

Python and JavaScript syntax checks were performed. Automated tests, browser
interaction checks and a paid real-model analysis were not run for this change.
This is a functional local individual-use implementation, not an institution-wide
production deployment or a claim that acceptance testing is complete.

Turnitin task/rubric synchronization, campus login, team calibration, advanced
citation verification, model training, OCR and automatic student delivery remain
outside this release. No fake similarity results, fictitious reviewers or sample
review tasks populate the primary UI. Existing legacy sample reports are excluded
from its metrics and lists. Existing stored assignments are retained for editing;
new installations no longer create a sample assignment automatically.

Before external deployment, complete the institutional identity/access plan,
backup/restore procedures and an authorized end-to-end acceptance exercise.
