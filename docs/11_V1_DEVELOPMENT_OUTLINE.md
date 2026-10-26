# V1 Development Outline — Individual Teacher Workflow

> Superseded for the current UI by [Labwise 1.2](UI_VERSION_1_2.md). Retained as historical design/implementation notes.

Decision date: 24 October 2026. Status: scope decision and implementation plan;
not a claim that the end-to-end workflow has been implemented.

## Scope review and decision

V1 validates one teacher completing one assignment review using their own grading
criteria. Remove Team and Calibration from the V1 product flow and navigation.
Retain it only in the development backlog. It must not block release or require
shared reviewer accounts, paired reviews or adjudication services.

This outline governs V1 scope where older six-module designs describe a broader
product. Existing detailed plans remain references for later releases. The
citation-verification charter continues to govern any future citation work; the
complete citation subsystem is not a dependency of the core V1 review release.
This decision changes planning only; removing existing prototype navigation is a
subsequent implementation task.

## One complete user journey

Create or select an assignment → enter requirements and import grading criteria
→ review and save the criteria → upload a student report → request AI analysis
→ inspect the source/map/suggestions → edit feedback and confirm scores
→ save and export teacher-approved feedback.

The working unit is one assignment and one report. The dashboard retains task
progress and resume actions, so a teacher can return to unfinished marking.

## Simplified navigation

1. Dashboard / 工作台: saved review tasks, assignment filter, factual progress,
   report import and resume review. Counts derive from saved task states.
2. Assignments and Grading / 作业与评分标准: assignment name, requirements and
   one criteria input accepting DOCX, text-based PDF or pasted text; saved
   assignments and edit/reuse actions beside it.
3. Settings / 设置: essential reading preferences and necessary service status.
   Model credentials remain server-side and outside the normal marking flow.

The existing three-column workspace opens from a task. Completed reviews and
exports remain accessible through the dashboard. A separate grading-standard
library and separate analytics page are unnecessary for V1: reuse a saved
assignment's criteria and show only basic task progress. Team and Calibration
has no V1 navigation entry, placeholder or mandatory setup step.

## Required functionality

### Assignment and personalized rubric

Preserve original imported text. Extract criterion names, descriptions, explicit
maxima/weights and performance descriptors when present. Show a readable editable
preview before teacher confirmation. Do not invent missing weights, silently
normalize inconsistent totals or present extraction as approval.

Personalization means applying the teacher-confirmed assignment requirements,
criteria, scoring scale and feedback-language preference. It does not mean
training a model per teacher or silently learning new grading policies from edits.
Teacher-provided feedback examples can be considered later and are not required.

If numeric scoring is requested, require confirmed per-criterion maxima and a
consistent total. A qualitative rubric may produce feedback without a numeric
score. Copying criteria creates an independent editable assignment. Editing a
saved rubric creates a new version; existing report reviews retain their original
rubric and requirements snapshot.

### Report import and analysis

For student reports, support parseable DOCX first. PDF and text support above
applies to grading-criteria import; scanned PDFs, OCR and complex report layouts
are deferred. Preserve original report text with stable paragraph references.
Show import/analysis progress, recoverable errors and retry actions.

Use the configured DeepSeek service through a server-side adapter. Each analysis
uses the confirmed requirements, rubric and report snapshot. Constrain output to
criterion-linked findings, source paragraph references, quotations, rationale,
candidate feedback and optional candidate scores. Validate structure, evidence
location and score bounds before display. Missing or invalid evidence is marked
for teacher verification. Student text is input evidence, never an instruction
to change the rubric or system behavior. Record model and analysis version.

### Three-column review

Left: report outline as the required initial map, with numbered green strengths
and red issues. Center: original report with evidence locations. Right: rubric
suggestions, teacher decisions, editable feedback, scores and private notes.

Keep a shared finding identifier across the map marker, source evidence and
suggestion card. Hover/focus highlights corresponding evidence; click locates it.
Support keyboard focus and touch selection. Color is accompanied by numbers and
text labels. Argument-map generation is a later enhancement; it does not block
V1 release.

Teachers accept, edit or reject suggestions and determine final scores. Private
notes stay separate from exported student feedback. Saving a draft and confirming
feedback are distinct actions. Changes after confirmation require fresh approval.

### Persistence and delivery

Save assignment versions, uploaded reports, analysis runs, teacher decisions,
confirmed scores and feedback so work survives a restart. Analysis retries must
not erase teacher edits. Use a minimal readable feedback export first (UTF-8 text);
retain an existing supported export if available, without making additional file
formats a release requirement. No automatic student delivery in V1.

## Minimal entity structure

- Assignment and AssignmentVersion: title, requirements, confirmed rubric snapshot,
  original criteria source, version and timestamps.
- Submission and DocumentVersion: assignment version, student alias, source file,
  extracted paragraphs and import state.
- ReviewTask: pinned document/rubric versions, current stage and saved draft.
- AnalysisRun and Finding: model/version, processing state, criterion, evidence,
  rationale and candidate content.
- TeacherDecision and CriterionScore: accepted/edited/rejected content, teacher
  score and confirmation; separate from AI output.
- FinalFeedbackVersion and ExportArtifact: confirmed output, source versions and
  export time; exclude private notes.

These can use the existing local storage and snapshots initially; V1 does not
require a new database per conceptual entity. Do not build CalibrationCase,
reviewer pairing, invitations or shared-resolution tables for V1. Preserve useful
stable identifiers so those features can be added later.

## Deferred functionality

Team collaboration, calibration cases, second marking, reviewer assignment,
disagreement statistics, adjudication and shared feedback libraries are backlog
items. Also defer advanced analytics, institutional login, LMS/Turnitin integration,
student portals, OCR, automatic delivery, custom model training and full citation
verification. Existing isolated prototypes may remain as development references;
they must not become prerequisites in the teacher's V1 workflow.

## Implementation order and release checks

1. Simplify the shell: three destinations, with assignment and criteria editing
   together; remove the calibration route from normal navigation. A task still
   opens the original three-column workspace.
2. Complete rubric import and confirmation: document/text input, readable edits,
   missing-score handling, saving, reuse and version isolation.
3. Connect the real report pipeline: DOCX parsing, stable evidence references,
   constrained analysis, persisted state, failure recovery and retries.
4. Complete teacher review: linked findings, editing, manual scoring, draft resume,
   confirmation and feedback export.
5. Validate the full journey using a real de-identified report and teacher-supplied
   rubric, including restart, rubric edit, analysis failure and reanalysis cases.

Release requires one teacher to complete that journey without visiting another
module or preparing team settings. Every displayed total must be factual or
explicitly labeled as an example. An exported score must be in the teacher's
confirmed scale, have an attributable rubric version and teacher confirmation.

The current interface includes sample review content and partially connected
services. Completing forms alone does not satisfy this release requirement.
Local individual-use V1 is not a campus-wide authenticated service. Any shared
or public deployment requires appropriate authentication and access isolation.

## Scope control

Prioritize a complete review journey over adding menu items. A proposed feature
enters V1 only if it is necessary to import criteria, review a report, preserve
teacher work or export confirmed feedback. Record other ideas in the
[development backlog](DEVELOPMENT_LOG.md). No delivery dates are committed here.
