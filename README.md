# Lab Report AI-Assisted Feedback Tool

## Current UI: Version 1.2.1

The active five-module interface now uses real saved data and editable review
operations. See [1.2.1 editable demo](docs/14_VERSION_1_2_1_EDITABLE_DEMO.md).
Configure a DeepSeek key in Settings to run the live connection/analysis tests.
These implementation notes supersede earlier fixed-sample descriptions below.


The active interface is the accepted teacher pilot with Team and Calibration
removed (five modules). Version 1.2.2 retains all six modules. Both source
snapshots are recorded in [UI version records](versions/README.md).
See [Labwise 1.2 UI outline](docs/UI_VERSION_1_2.md).
This baseline takes precedence over the later editable-product descriptions below.

A project to help university instructors understand and review English lab reports. The pilot focuses on one course, one report type, and DOCX files. It helps instructors inspect report structure, locate source evidence, review rubric-aligned suggestions, and prepare feedback.

## Project Documentation

- [引用验证模块开发纲领](docs/CITATION_VERIFICATION_CHARTER.md): governing design for all subsequent citation-verification development.
- [图表自动发现与科学审核模块开发纲领](docs/VISUAL_RECOGNITION_CHARTER.md)：后续图表识别、原页目录、图注关联和批量审核开发的执行依据。

- [Project plan and design brief](PROJECT_BRIEF.md): product scope, three-column review workspace, report map types, pilot data analysis, model-use constraints, privacy principles, and rollout plan.
- [Historical writing baseline](corpus/historical/BASELINE_ANALYSIS.md): de-identified writing samples, teacher feedback patterns, confirmed scoring rules, and the reusable analysis template.
- [Citation verification plan](docs/06_CITATION_VERIFICATION.md): reference matching, citation-style checks, scholarly-search integration, claim support review, safeguards, and rollout phases.

## Core Workflow

Upload a DOCX → parse the document and assign paragraph IDs → generate a report outline and argument map → produce evidence-linked candidate suggestions against the current assignment rubric → instructor review, editing, and confirmation → export feedback.

## Design Boundaries

AI provides reviewable drafts and candidate feedback only. Report maps are not grading decisions. Suggestions without source evidence require instructor verification. Instructors control final scores, feedback, and any student-facing communication. Results from Turnitin or similar services are shown as separate reference material and do not automatically establish academic misconduct.

The project is currently in the pilot planning and interactive prototyping stage. A fixed-host Crossref metadata-search prototype is available for citation review; DOCX parsing, automated citation extraction, full-text evidence analysis, formal grading, and feedback delivery have not been implemented.

## Local preview

The scholarly search endpoint now queries Crossref, PubMed and Europe PMC concurrently. Results are merged by DOI, PMID or PMCID, with source provenance retained and partial results returned when a provider is unavailable. PubMed requests are throttled across local threads. Set optional `NCBI_API_KEY` on the server for the higher NCBI request allowance; never place it in browser code. `LABWISE_CONTACT_EMAIL` identifies NCBI requests. Full-text retrieval and automated claim-support analysis remain future work.

```bash
python3 -m pip install -r requirements.txt
python3 server.py
```

Open `http://127.0.0.1:8000/#workspace` and select **引用核验**. For responsible Crossref production use, set `LABWISE_CONTACT_EMAIL` to an operational contact address; use `LABWISE_PORT` to override the local port.


## Teacher Pilot Interface

The canonical entry now loads real saved reports and editable review operations.
See [Editable teacher product](docs/13_EDITABLE_TEACHER_PRODUCT.md) for the current
implementation. This supersedes older descriptions of a fixed sample workspace
below. Campus deployment and live Turnitin synchronization remain future work.

Run `python3 server.py` and open <http://127.0.0.1:8000/>.
On macOS, `start.command` starts the same interface at port 8001.
The teacher dashboard is the single product entry: task summaries and review
assignments lead to the original three-column review workspace. Assignment and
rubric import/editing is integrated into this dashboard. The former `/pilot.html`
entry now redirects to `/`.

The review workspace currently retains its interactive sample content. Assignment
settings support local Word/PDF text extraction and pasted grading criteria,
with readable previews and persisted edits. Existing report rubric snapshots are
preserved when assignment settings change.

The six sidebar modules and their target entities are documented in
[Navigation and domain model](docs/09_NAVIGATION_AND_DOMAIN_MODEL.md).

Future school sign-in, LMS entry and Turnitin authorization are planned in
[Identity and institutional access](docs/10_IDENTITY_AND_INSTITUTIONAL_ACCESS.md).

### Original document preview

The main demo opens uploaded PDFs in the browser PDF viewer, retaining their original pages. DOCX files are converted locally to PDF using LibreOffice (`soffice` or `libreoffice` on PATH). Docker includes LibreOffice Writer and Noto CJK fonts. For exact Word pagination, export to PDF from Word before uploading; missing fonts and complex objects can affect conversion. Uploaded previews disable the sample review panels because their evidence is not linked to the uploaded document. PDFs remain in browser memory; DOCX conversion uses temporary local files that are removed after conversion. Preview does not save the report or generate grading results.

### Saved-report original viewer

Saved report review now defaults to original-page rendering using locally bundled Mozilla PDF.js 5.6.205 (license in `vendor/pdfjs/LICENSE`), without depending on a browser PDF plugin or remote CDN. The reader supports page navigation, selectable text, fit width/fit page and zoom. Word uses the existing local DOCX-to-PDF conversion. The review surface is exclusively the original file. Navigation and analysis suggestions highlight their quoted evidence inside the original PDF text layer; a missing match requires manual review and never opens a reformatted text view. Teachers can select text on a page, add a comment, and save page/quote/comment anchors with the review draft. Comments enter student feedback only when the teacher chooses to add them. The AI service still analyzes extracted document text; this UI change does not add image or layout reasoning. Missing source files show an explicit error and a retry option. The reader and worker resources are included in the Docker image.

### AI analysis verification (2026-10-24)

The live DeepSeek Flash endpoint was tested with a fictional DOCX report, fictional assignment and rubric. It returned a saved overview and four evidence-linked findings; the browser successfully highlighted a finding in the original document viewer. The review page now defaults to AI analysis, labels structure-only mode explicitly, and presents the AI overview separately from the editable teacher overview. Failure messages leave the controls ready to retry.

Regression commands: `python3 -m unittest discover -s tests -q`, `node tests/test_ai_workflow.js`, `node tests/test_original_preview.js`. Tests cover API request format, rejected fabricated evidence, incomplete responses, missing credentials, network failure/retry, preserved teacher comments/scores, and persisted analysis. The old tests now create their own assignment fixtures instead of relying on an automatically seeded sample course.

The fictional live-test output is in `dist/ai-analysis-test-result.json`; its document is `examples/ai-analysis-test.docx`. No student report was sent in this verification. API parameters were checked against https://api-docs.deepseek.com/api/create-chat-completion/.

### Article outline navigation

The review sidebar now presents a Notion-style document tree: source headings establish the section/subsection hierarchy, and existing AI claims appear under their most specific common parent section. Review findings remain in the teacher review panel. Nested headings can be expanded, collapsed, searched or renamed; each node locates its evidence in the original document. Markdown export includes a preview and a downloadable `.md` file with argument bullets under the correct owning heading. Missing article sections are not invented from the assignment rubric.

Validation includes the source hierarchy/common-parent/Markdown regression suite (`node tests/test_document_outline.js`), browser search and collapse checks, direct navigation to a third-level heading on PDF page two, and an actual Markdown download.


### Word-first review (1.2.1, 25 October 2026)

New student and rubric file uploads accept DOCX only. Word paragraphs, tables and embedded images enter automatic DeepSeek analysis; suggestion decisions are explicitly confirmed/reopened. Completed assignments export original Word files, commented copies and score data. See [workflow and implementation limits](docs/19_WORD_FIRST_REVIEW_WORKFLOW.md). The reading view may differ from Word layout. Native charts require a local layout converter for visual inspection; configure `LABWISE_SOFFICE` when needed. Historical PDF records remain readable and must be archived or replaced before a Word-only assignment package export.
