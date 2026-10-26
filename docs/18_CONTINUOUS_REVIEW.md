# Continuous assignment review — 1.2.1

Updated 25 October 2026.

## Teacher workflow

Each assignment branch offers Start Review or Continue Review. Continue opens the last unfinished submission, then other saved drafts, then untouched submissions in stable import order. Archived submissions and confirmed reports are excluded. Opening a report establishes a persistent checkpoint. Saved teacher edits remain in the existing report payload; opening a report does not modify scores or confirm feedback.

Report grading states are Not Started, In Progress and Completed. Completion requires instructor confirmation. AI queued/running/ready/failed states remain separate. Older reports containing teacher edits are recognized as drafts. Branches show the last unfinished file and in-progress counts; filtering supports each grading state.

Save Draft retains the current report and allows interruption. Unsaved edits retain the existing leave-page warning; this feature does not introduce automatic draft saving. Teachers should save before closing the browser.

Confirm and Review Next validates and saves the full current review first, then opens another unfinished submission from the same assignment. The last report remains open with feedback export available and an assignment completion message. Incomplete reviews or failed saves do not advance the queue. If opening the next file fails after a successful confirmation, the confirmed result remains saved and the assignment's Continue Review entry resumes the queue.

## Persistence

SQLite review_progress stores started/opened/saved timestamps, review_sessions stores one checkpoint per local assignment, and review_order freezes the submission sequence independently of AI completion timestamps and report replacement. These tables are separate from model job state and report revision checks. They survive browser refresh and server restart on this local installation. This is not a multi-teacher assignment or locking system.

Endpoints: POST reports/{id}/start-review; POST assignments/{id}/continue-review. The bootstrap summaries include grading_state, review_progress and import_order. Checkpoint writes run inside an immediate transaction and never overwrite document content or teacher feedback. Existing save/confirm validation and revision protection remain enforced.

Implementation checks: Python/JavaScript syntax checks and direct observation of the continuation entry and current-report status. No automated tests were added or run, and existing grades were not confirmed for demonstration.
