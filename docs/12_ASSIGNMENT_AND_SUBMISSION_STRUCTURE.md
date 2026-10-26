# Assignment Topics, Types and Submission Batches

> Superseded for the current UI by [Labwise 1.2](UI_VERSION_1_2.md). Retained as historical design/implementation notes.

Decision: 24 October 2026. Supplements the V1 development outline.

## Teacher workflow

Create an assignment topic → edit title, assignment type, task instructions and
rubric → inspect and save the grading criteria → import multiple student files
under that topic → review submissions individually against their pinned rubric.

“Assignment” means one teacher-defined task, not a student's submitted document.
“Type” is an editable category such as lab report, essay, research report or case
analysis; it does not silently select another grading policy. “Submission” means
one student file. V1 assumes one primary task per assignment, with no nested
question bank, multipart exam or team-review workflow.

## Framework and persistence

The existing Assignment entity now carries assignment_type and external_task
alongside title, instructions, rubric and revision. Existing records default to
lab report. Assignment edits retain the previous snapshot; each imported report
captures its own complete assignment/rubric snapshot. A browser batch sends the
expected assignment revision with each file so a concurrent rubric change cannot
silently mix criteria within that batch.

The assignment editor contains the task fields and one rubric import area.
Saved assignments remain beside it. Below a saved assignment is a multiple-file
student-submission area, per-file progress/errors and a saved submission list.
The list is an import/status view; the existing example review workspace is not
thereby converted into a complete real-report marking pipeline.

V1 batch support: up to 30 DOCX files, at most 10 MB each, sent sequentially to the
existing report endpoint. Each successful import is persisted independently.
Failures do not discard successful files. Retry only unfinished entries. Upload
does not start billable model analysis or send data to another platform. The
criteria import area still accepts DOCX, text-based PDF or pasted rubric text.
A submission filename is a display label, not verified student identity.

## Turnitin handoff

The optional target-task field stores an unverified human-readable reference.
It is not an authenticated external assignment ID or proof of a live connection.
Export the saved title, type, requirements, rubric and local version as a readable
manual-entry text summary. This is not a Turnitin-native import file. Teachers
copy and check fields in their authorized platform; scales and performance levels
may require additional configuration there.

Direct creation/update of Turnitin grading tasks or rubric attachment is deferred
until the institution confirms the exact product and supported API operations.
Turnitin Core API documentation describes submission/upload/similarity-report
operations, not a guarantee that this application's assignments and rubrics can
be written into an existing Feedback Studio marking task:
[official Core API guide](https://developers.turnitin.com/turnitin-core-api/migrating-from-ithenticate-api).

A future authorized connector must store institution/installation/external-task
IDs separately from display text, map confirmed local versions, preview changes,
require an explicit teacher action, avoid duplicate creates, handle conflicts and
record receipts/failures. Keep local edits usable during connection failures.
No grade release or student upload is implied by an assignment synchronization.

## Current implementation boundaries

The framework adds editable type and target reference, persistence migration,
batch submission import, saved-file statuses and manual-entry summary export.
Navigation is reduced to Dashboard, Assignments and Grading, and Settings.
Team and Calibration is inaccessible through V1 navigation and remains backlog.
No external credentials, live Turnitin calls, automatic rubric synchronization,
student identity matching or new real-report review UI are included.

## Follow-up acceptance requirements

Check assignment editing/reopening and old-record migration; batch mixed-file
errors, retries and saved counts; rubric changes during upload; report snapshot
isolation; manual summary field fidelity; and no accidental external requests.
These are pending verification requirements, not completed test results.
