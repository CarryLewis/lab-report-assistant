# Development Decisions and Backlog

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
