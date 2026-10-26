# Automatic AI analysis — Labwise 1.2.1

Updated 25 October 2026. This workflow supersedes earlier instructions requiring teachers to start report analysis manually.

## Teacher workflow

Upload a report or import a batch under a saved assignment and rubric. Each eligible report enters a persistent background queue and uses the configured official DeepSeek service. The file list shows queued, analyzing, ready, connection required or failed states. Open a ready file to read its summary, argument outline and candidate feedback immediately. Opening an already analyzed file does not repeat the model request.

The review workspace no longer has a manual text-analysis button or mode selector. It displays automatic analysis status and refreshes completed results. Teacher scores, notes, feedback, annotations and existing visual reviews are retained. Unsaved teacher edits are protected when background results arrive; save edits before displaying the new result.

## Queue and recovery

Jobs are stored in SQLite and processed sequentially outside the upload request. A missing key pauses jobs; saving a connection resumes them. Failed jobs offer an explicit retry in the file list. Jobs interrupted by a stopped process require retry rather than silently repeating a potentially billed request. Archived and confirmed reports are skipped. Existing unfinished reports are enrolled during startup.

## Boundaries

Automatic analysis covers extracted report text against its rubric. Targeted scientific image review remains a separate teacher action and must not be represented as automatically completed visual verification. AI completion does not confirm grades or release student feedback. Upload notices identify DeepSeek as the processing service.

## Implementation observations

Python and JavaScript syntax checks were completed. Existing queued reports produced saved DeepSeek results; the current report opens directly with four candidate suggestions and retains two previous visual reviews. No new automated test suite was added or run for this change.
