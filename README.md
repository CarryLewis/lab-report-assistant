# Lab Report AI-Assisted Feedback Tool

A project to help university instructors understand and review English lab reports. The pilot focuses on one course, one report type, and DOCX files. It helps instructors inspect report structure, locate source evidence, review rubric-aligned suggestions, and prepare feedback.

## Project Documentation

- [Project plan and design brief](PROJECT_BRIEF.md): product scope, three-column review workspace, report map types, pilot data analysis, model-use constraints, privacy principles, and rollout plan.
- [Historical writing baseline](corpus/historical/BASELINE_ANALYSIS.md): de-identified writing samples, teacher feedback patterns, confirmed scoring rules, and the reusable analysis template.
- [Citation verification plan](docs/06_CITATION_VERIFICATION.md): reference matching, citation-style checks, scholarly-search integration, claim support review, safeguards, and rollout phases.

## Core Workflow

Upload a DOCX → parse the document and assign paragraph IDs → generate a report outline and argument map → produce evidence-linked candidate suggestions against the current assignment rubric → instructor review, editing, and confirmation → export feedback.

## Design Boundaries

AI provides reviewable drafts and candidate feedback only. Report maps are not grading decisions. Suggestions without source evidence require instructor verification. Instructors control final scores, feedback, and any student-facing communication. Results from Turnitin or similar services are shown as separate reference material and do not automatically establish academic misconduct.

The project is currently in the pilot planning and interactive prototyping stage. A fixed-host Crossref metadata-search prototype is available for citation review; DOCX parsing, automated citation extraction, full-text evidence analysis, formal grading, and feedback delivery have not been implemented.

## Local preview

```bash
python3 -m pip install -r requirements.txt
python3 server.py
```

Open `http://127.0.0.1:8000/#workspace` and select **引用核验**. For responsible Crossref production use, set `LABWISE_CONTACT_EMAIL` to an operational contact address; use `LABWISE_PORT` to override the local port.

