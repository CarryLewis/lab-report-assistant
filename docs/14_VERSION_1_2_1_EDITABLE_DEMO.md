# Labwise 1.2.1 — Editable Demo and API Integration

Updated 24 October 2026. Active version remains 1.2.1. The accepted white header,
dark sidebar, five modules and three-column review layout are retained. Version
1.2.2 remains the separately recorded variant with Team and Calibration.

## Functional modules

01 Dashboard reads actual saved reports and derives pending, failed and confirmed
progress. Search, status filtering, resume marking, file import and archiving use
real records. No canned task rows or percentages populate the active page.

02 Courses and Assignments supports editable titles, types, requirements, imported
or manually entered numeric rubrics, criterion-level editing, reuse and archival.
Each assignment can receive a batch of independently saved student reports.
Imported rubric source is retained separately from normalized edited criteria.

03 Grading Standards displays only saved assignment rubrics, with edit and reuse
actions. No automatically inserted reference rubric stands in for a teacher's
standard. Empty libraries offer creation rather than invented content.

04 Review Analytics reads actual local report states and filters by assignment.
It does not treat model completion as teacher confirmation or invent score charts.

05 Settings and Activity saves teacher name, course label, term and reading
preferences on the server. It offers DeepSeek configuration, key clearing,
connection checking and a real structured-analysis test. It also lists recoverable
archived records. Browser-local action history is informational, not a formal
institutional audit trail.

## Real review workflow

An imported DOCX or text-based PDF opens its own paragraphs and pinned rubric.
Overview, outline/argument navigation titles and nodes, candidate feedback,
criterion scores, final feedback and private notes are editable and saved.
Findings share IDs across map markers, source evidence and review cards. Teachers
accept, edit or reject candidates. Source text itself remains immutable so evidence
references retain meaning; upload a revised document as another submission.

Draft save, teacher confirmation, version history/restore, report metadata,
archive/restore and confirmed Word/text/print exports call the existing backend.
Exports exclude private notes and require current teacher confirmation.
Reanalysis retains teacher scores and final feedback, preserves previous revisions
and requires review of the newly generated findings.

New uploads retain an integrity-checked source file for the original-page preview.
PDF can be viewed directly. DOCX preview uses the existing local conversion service
and requires its converter dependency; a conversion failure leaves the evidence
text usable. Legacy records without the original binary need reimport for page
preview. Browser PDF pages and evidence paragraphs are separate views: selecting
a finding returns to evidence text. No exact PDF-page coordinate mapping is implied.

## API contracts

- GET bootstrap: real assignments, non-sample reports and non-secret settings.
- POST rubric-import / assignments: extract, validate, save and version criteria.
- POST reports: parse and persist each uploaded report, with optional idempotency
  token and expected assignment revision.
- GET reports/{id}/source: integrity-checked original file, encoded for local preview.
- POST reports/{id}/analyze: structure extraction or real DeepSeek analysis.
- POST reports/{id}/save or confirm: validated scores, teacher edits and decisions.
- GET reports/{id}/revisions; POST restore: recoverable report versions.
- GET reports/{id}/export[-docx|-html|-turnitin]: confirmed feedback outputs.
- POST preferences / settings: reading/course configuration and service settings.
- POST connection: authenticated request to the provider's model-list endpoint.
- POST test-analysis: send a short, synthetic method paragraph and rubric to the
  real provider, validate its JSON and evidence references, return a success receipt
  only on an actual valid response. No student report or fake analysis is used.
- GET archived; POST archive/unarchive: reversible record management.

DeepSeek requests follow the official
[model list](https://api-docs.deepseek.com/api/list-models/) and
[chat completions](https://api-docs.deepseek.com/api/create-chat-completion/)
contracts. Default destination is https://api.deepseek.com. API keys stay in server
memory or the deployment environment, not browser storage, source files or SQLite.
The current preview has no configured key: real provider verification is pending
configuration. There is no mock-success fallback and import does not trigger AI.

## Validation record

Python/JavaScript syntax checks and static element-reference checks passed.
An isolated temporary database exercise passed: empty state, rubric save, real
DOCX parsing, upload idempotency, original-file retrieval, structure extraction,
draft save, numeric confirmation, Word export, private-note exclusion, reanalysis
preservation, history restore, archive/restore and course preferences.
Missing-key testing correctly failed instead of claiming AI connectivity.
The browser loaded the five-module dashboard, settings and an existing real report
with editable scores/feedback. No existing student record was edited for checks.
A paid provider completion has not been validated because no key is configured.

## Limits

This is a local individual-teacher demo, not a campus-hosted authenticated service.
Team/calibration, live Turnitin write-back, automatic student delivery, OCR and
full citation/visual verification are outside this version. No simulated panels
for those features are loaded into the active review page. The existing institution
access design remains a prerequisite for a shared deployment.


## 2026-10-25 — Automatic report analysis (1.2.1)

Uploads and batch imports now queue DeepSeek text analysis automatically. File status and saved results are visible directly; the manual analysis selector/button is removed. Teacher review and confirmation remain required. See [automatic analysis workflow](17_AUTOMATIC_AI_ANALYSIS.md).
