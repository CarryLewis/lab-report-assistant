# Word-first review workflow — Labwise 1.2.1

Updated 25 October 2026. This design supersedes PDF submission and manual image-analysis instructions in earlier implementation notes. Version 1.2.2 remains a separate snapshot.

## Product flow

1. Create an assignment, requirements and a teacher-owned rubric. Import rubric content from DOCX or enter text.
2. Submit student work as DOCX only (single or batch). Reject PDF and legacy DOC. Retain original bytes, a SHA-256 digest and the assignment/rubric snapshot.
3. Queue automatic analysis. Read Word paragraphs, table rows/cells, embedded raster images and native chart caches. Submit embedded images with text to the official DeepSeek image-capable model. For native charts and other drawings, attempt an internal local layout rendering; students do not submit PDF. No teacher crop-and-send step is part of this workflow.
4. Show AI summary, outline, suggestions and figure coverage. Each suggestion references an actual Word paragraph, exact text when available, and an object ID for a non-text figure. Hover or click to locate the same paragraph in the Word reading view. Source hash and XML paragraph index are the authoritative anchor, not guessed page numbers.
5. Review each suggestion. Pending suggestions have editable feedback, Confirm Suggestion and Do Not Adopt actions. A decision is saved immediately. A confirmed card displays the decision and fixed feedback, with only Modify remaining. Modify explicitly reopens the item and invalidates final report confirmation. Revisions retain previous decisions.
6. Enter criterion scores and optional overall feedback. Confirm and Review Next validates all scores and suggestion decisions, then commits scores, annotations, feedback and review status before opening another unfinished report in this assignment. Validation/save failures do not advance. Save Draft retains unfinished work and the previous per-assignment checkpoint. Unsaved edits still require Save Draft before closing.
7. After all active submissions in an assignment are confirmed, Export Review Package downloads one ZIP. A confirmed individual submission also offers a package download from its export dialog.

## Export deliverables

- `originals/`: original Word files, byte-for-byte unchanged.
- `reviewed/`: copies of the original Word files with native Word paragraph comments for accepted/edited feedback, teacher annotations and a grading-summary comment. The body is not rewritten. Existing Word comments and package assets are retained.
- `feedback/`: an academic feedback summary per report, with criterion scores, numbered evidence and final feedback.
- `scores.csv`: student/file identity, total, maximum, criterion scores and confirmation timestamp; user labels are escaped against spreadsheet formula interpretation.
- `feedback.json`: evidence, Word comment anchors, source digest and grading data. Private teacher notes are excluded.

The layout follows familiar academic marking patterns: document + numbered comments + rubric + final feedback. This is a Labwise export, not a proprietary Turnitin import file or authenticated Turnitin synchronization. Word must have comments visible under Review to display the annotations.

## Evidence and decision rules

- Text evidence must be an exact substring of a referenced paragraph. A figure-only finding may omit the quote only when its object ID belongs to that paragraph.
- No ungrounded anchor is created. Ambiguous historical text must be relinked by reimporting rather than guessed at export.
- Confirmed suggestions are protected by server validation as well as a compact read-only card. Explicit reopening is required before changing the decision or feedback.
- Accepting a suggestion does not rewrite a student's submission. The teacher confirms feedback and scoring, not an AI-generated replacement answer.
- AI completion is distinct from teacher completion. No AI-generated grades or automatic release to students are introduced.

## Model and parsing boundary

The official image input guide is https://api-docs.deepseek.com/guides/vision/ (checked 25 October 2026). DOCX is a ZIP/XML package, not a raw model attachment: the backend extracts content and provides source IDs; it sends embedded images using the official image blocks. Word-native analysis is routed to `deepseek-flash` so images cannot silently reach a text-only model.

Embedded PNG/JPEG/GIF/WebP images are normalized locally. Native charts supply cached data and an internal layout rendering when the local converter is available. External linked assets are not fetched. Unsupported OLE, vector objects, charts lacking a rendering and resource-limit exclusions remain visible as incomplete coverage. Header/footer/footnote content is flagged as outside the current main-body grading scope.

Current demo limits: 10 MB DOCX upload, 40 MB expanded package, 100,000 source-text characters; up to 40 embedded image inputs and 20 MB source images; fallback layout rendering up to 30 pages and 24 MB images. Exceeding a visual limit is reported, not treated as a completed visual review. Image observations do not establish precise measurements, replicates or significance. A separate scientific/statistical validation system would be needed for those claims.

## Word display and anchoring

The Word reading view renders text, tables and common embedded images with stable source paragraph anchors. It is not Microsoft Word's layout engine and may differ in pagination, equations or drawing layout. Native chart caches are shown with a prompt to check the original Word's appearance. The original download and exported original preserve all bytes. Comments in the first implementation are anchored to complete source paragraphs; exact evidence sentences are included in the comment text. Character-level comment ranges can be added later without changing the evidence model.

## Implementation and legacy records

New modules: `word_source.py`, `word_export.py`, `word-reader.html/js/css`. Existing upload, background analysis, review checkpoint, suggestion validation and grouped-dashboard flows are extended. Existing PDFs and old AI results are retained as historical records, not silently converted or reanalyzed. An assignment containing active historical PDFs must have them archived or replaced by Word before a Word-only batch export.

Python and JavaScript syntax checks are used during implementation. No automated test suite is added or run unless requested. Existing student marks are not confirmed for demonstration. Model output and large/complex Word compatibility still require pilot acceptance with representative teacher-provided files.

## Implementation observation — 25 October

The existing complex Word opens in the anchored reading view and a saved candidate locates its actual methods paragraph. Previously confirmed candidate cards retain their decisions with only Modify visible. A separate local fictional Word containing text, a chart image and a table was exported with native comment ranges and successfully rendered with bundled LibreOffice; the page was visually inspected. OPC namespace serialization was corrected during that check. Existing teacher scores and decisions were preserved. New multimodal DeepSeek requests and full assignment-package acceptance have not been exercised against a representative newly submitted Word in this change.

Optional local rendering configuration: set `LABWISE_SOFFICE` to the approved local LibreOffice executable. The current local service uses the bundled runtime; Docker uses its installed container converter.
