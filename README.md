# Lab Report AI-Assisted Feedback Tool

A project to help university instructors understand and review English lab reports. The pilot focuses on one course, one report type, and DOCX files. It helps instructors inspect report structure, locate source evidence, review rubric-aligned suggestions, and prepare feedback.

## Project Documentation

- [引用验证模块开发纲领](docs/CITATION_VERIFICATION_CHARTER.md): governing design for all subsequent citation-verification development.

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
