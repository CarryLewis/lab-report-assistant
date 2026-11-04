# Development Decisions and Backlog

## 2026-10-26 — Simplify release interface copy

Removed AI helper explanations from the active dashboard, upload forms, review sidebar, outline footer and help dialog. Review headings now use 报告概览 and 评阅建议; queue and processing labels use neutral, concise statuses. Removed repeated teacher-decision disclaimers and model names from report result metadata. Service settings retain functional model/key controls and connection states. Automatic processing, source data, grading decisions and exports are unchanged; historical snapshots and development documentation remain intact. JavaScript/Python syntax and active dashboard/review/settings rendering were checked with the isolated fictional fixture.

## 2026-10-25 — Implement local visual discovery and original-page inventory

Added resumable local page scans for embedded images, vector groups and tables,
page coverage/error states, thumbnail inventory, source/preview version checks,
teacher corrections and local region saving. Word viewing and detection share a
pinned PDF. Candidate review reuses the existing explicit-send visual dialog.
See [implementation and verification](16_VISUAL_DISCOVERY_IMPLEMENTATION.md).
OCR, semantic classification, multi-panel linking and batch scientific review
remain later stages; no universal recall claim is made.

## 2026-10-24 — Establish the visual recognition development charter

Recorded the user-approved direction for automatic figure discovery in
[图表自动发现与科学审核模块开发纲领](VISUAL_RECOGNITION_CHARTER.md).
Future implementation must follow its staged pipeline: local discovery and
page coverage, classification and caption/body linking, original-page inventory
with teacher corrections, then batch scientific review. The charter defines
coordinate/version contracts, evaluation requirements and explicit external-send
boundaries. This change documents the development plan; it does not implement
automatic detection or establish successful live vision testing.

## 2026-10-24 — Support complex DOCX preview

Replaced whole-document external-resource rejection with a sanitized temporary
preview copy, cached chart/image rendering and a sandboxed readable fallback.
Restored the valid 1.2.1 stylesheet after detecting HTML content in the CSS file,
and fixed the PDF reader container positioning and toolbar measurement. The
previously failing report now renders as seven pages in the browser. Original
files and grading data remain unchanged. See the complex-preview design note.


## 2026-10-24 — Tidy the 1.2.1 review header

Separated global navigation from report identity and review actions. Removed the
duplicate workbench return from the global bar during review, put status below
the filename, grouped secondary and grading actions, and added responsive wrapping
and filename truncation. Existing action IDs and handlers are retained. Verified
the updated header visually in the current browser; no grading or API behavior
changed.


## 2026-10-24 — Activate the 1.2.1 editable demo

Retained the accepted five-module shell and connected actual assignment, report,
review and export records. Removed canned dashboard/workspace material and added
real DeepSeek connection and structured-analysis probes. Isolated local API checks
passed; current preview lacks a key, so provider completion remains unverified.
See [implementation and validation record](14_VERSION_1_2_1_EDITABLE_DEMO.md).
The retained 1.2.2 variant was not changed.


## 2026-10-24 — Record 1.2.1 and 1.2.2

Active UI is 1.2.1: remove Team and Calibration and renumber the remaining five
modules. Retain the six-module variant as 1.2.2. Both frontend source snapshots
and file-hash manifests are stored under versions/. Local user data and existing
calibration notes are unchanged. No new collaboration backend is implied.


## 2026-10-24 — Restore and designate UI version 1.2

User selected the screenshot's six-module teacher pilot as the accepted UI.
Restored its shell, dashboard and review workspace, withdrew the later replacement
entry and reinstated the original assignment editor. VERSION is 1.2 and the header
shows v1.2. See [accepted UI outline](UI_VERSION_1_2.md). Existing local user data
and compatible backend storage are preserved. Earlier scope reductions and editable
replacement notes below are historical where they conflict with this decision.


## 2026-10-24 — Connect the editable teacher workflow

Replaced the static sample entry with the actual saved-report dashboard and
three-column review workspace at `/`. Added overview/map-title persistence,
real score/feedback editing, version recovery, report metadata, archive/restore,
assignment reuse and server-persisted reading preferences. Existing feedback
exports and guarded model analysis are connected to the same workspace.
See [implementation record](13_EDITABLE_TEACHER_PRODUCT.md) for limits.
Python/JavaScript syntax checks completed; functional acceptance is pending.

## 2026-10-24 — Reduce V1 to individual teacher review

Requested decision: remove Team and Calibration from the first release and retain
it as future planning. Approved product direction: core dashboard, report import,
teacher-owned grading-criteria import and personalized assisted review.

The [V1 development outline](11_V1_DEVELOPMENT_OUTLINE.md) defines the resulting
scope, navigation, minimal entities, delivery sequence and release checks.
Documentation updated; UI removal and end-to-end implementation remain pending.

### Deferred: Team and Calibration

Purpose: help multiple authorized reviewers compare judgments against the same
report and rubric version, discuss evidence and record an authorized resolution.

Potential capabilities: reviewer assignment, shared calibration cases, independent
initial judgments, criterion-level disagreement views and adjudication history.
Never overwrite individual judgments or automatically average disagreement away.

Dependencies before scheduling: validated individual review workflow, real user
identity and course permissions, shared storage, immutable rubric/document
versions, attributable decisions and appropriately protected activity history.

Reconsider after the individual teacher pilot demonstrates a concrete need for
multiple reviewers and institutions can provide authorized participants and data.
No committed release date. No V1 placeholder page or team setup requirement.


## 2026-10-25 — Automatic report analysis (1.2.1)

Uploads and batch imports now queue DeepSeek text analysis automatically. File status and saved results are visible directly; the manual analysis selector/button is removed. Teacher review and confirmation remain required. See [automatic analysis workflow](17_AUTOMATIC_AI_ANALYSIS.md).


## 2026-10-25 — Assignment-grouped review dashboard (1.2.1)

Replaced the flat report list with collapsible assignment branches. Each branch shows all active submissions, teacher-confirmed (graded) and unconfirmed (ungraded) counts and progress. AI readiness stays separate from grading completion. Empty saved assignments remain visible. Search and grading filters apply to child files while branch totals retain the full assignment count. Branch expansion is retained through automatic polling; unchanged data does not rebuild the list. Version 1.2.2 remains unchanged.


## 2026-10-25 — Continuous assignment review (1.2.1)

Added per-assignment start/resume actions, persistent unfinished-report checkpoints, grading status filters and automatic progression after successful teacher confirmation. Stable import order is independent of background AI updates. Save drafts before closing; confirmation still requires complete scores and reviewed feedback. See [continuous review workflow](18_CONTINUOUS_REVIEW.md).


## 2026-10-25 — Word-first automatic review (1.2.1)

Adopted DOCX-only submissions, automatic text/table/image inputs with source anchors, explicit immutable suggestion decisions, continuous grading and original/annotated Word plus score-package export. Manual crop-and-send image analysis is retired from the active UI. See [complete workflow and limits](19_WORD_FIRST_REVIEW_WORKFLOW.md).
## 2026-10-27 — Local downloadable application direction

Current delivery is an individual teacher application downloaded and run on the teacher's own computer. Prioritize durable local review, installation/startup, backup/restore and data-preserving updates. Turnitin sync/sign-in, LMS/SSO and central multi-user deployment are deferred. Added the local delivery charter and marked older institutional integration plans as historical. Documentation change only; no runtime, packaging or synchronization code changed.

## 2026-10-28 — Multi-genre writing review (1.3.0)

Added eight editable genre profiles, 80 original draft wording examples, eight fictional text fixtures, template preview/application and the standards-library entries. Analysis now uses the submitted genre/language and only matching wording references; assignment imports freeze the writing profile alongside the rubric. Custom types fall back to general writing guidance. See [implementation and validation](24_MULTI_GENRE_WRITING.md).

## 2026-10-29 — Preserve code parsing and add AI rubric understanding/scoring

Added an explicit code/AI method selector. Code mode retains local rubric parsing and the prior feedback/manual-score workflow; AI mode interprets natural rubric text and produces evidence-linked candidate scores. Separate drafts, method metadata and report snapshots preserve both workflows. Added validation for weights, source quotes, score coverage, uncertain scores and special-rule arithmetic/caps. See [implementation and verification](25_DUAL_RUBRIC_PROCESSING.md).

## 2026-10-29 — Preview rubric imports beside the editor

Word imports and pasted rubric text now automatically use the selected code/AI method and open an editable preview beside the source. The preview appears before the saved-assignment library and shows reading, processing, source-changed and recoverable failure states. Manual AI text edits retain an explicit Update preview action. Preview edits preserve original AI source text. Added regression coverage for both methods and verified paste/edit behavior in an isolated browser fixture using simulated AI responses. Existing packaged-app data was left untouched.


## 2026-10-31 — Synchronize the 1.3.4 development snapshot

Published the accumulated local development source: multi-genre writing profiles, code/AI rubric processing and editable previews, Chinese/English UI, desktop runtime and backup/restore, import recovery, and review-PDF export with numbered margin comments. The source version is 1.3.4; the macOS installation notes retain their original build-specific dates and acceptance results. No installer or GitHub Release is published by this source synchronization.

Before synchronization, all 100 Python tests (`.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`) and all nine `tests/test_*.js` scripts passed. No live AI benchmark or new packaged-app acceptance run was performed. Updated both READMEs to reflect this source snapshot.

Excluded the entire generated `output/` directory, as well as historical corpus, local databases, rendered student documents and credentials. Added missing rubric/profile modules and the public writing-profile catalog to the Docker resource list; the Docker image was not rebuilt in this synchronization.


## 2026-11-04 — Synchronize the 1.3.6 development snapshot

Consolidated changes since 1.3.4: shared typography and controls, compact three-pane review layout, embedded reader adjustments, and eight independently selected AI evaluation languages. Text review, scoring and visual explanations share the language contract while source quotes stay verbatim. Updated runtime/packaging resources and filled missing Docker resources.

All 103 Python tests and ten JavaScript test scripts passed before synchronization. No new live-model, browser visual, Docker-build or packaged-app acceptance run was performed. See [1.3.6 progress and validation](26_RELEASE_1_3_6.md). Private historical corpus, runtime data, credentials and generated output remain excluded.
