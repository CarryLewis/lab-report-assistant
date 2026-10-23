# Lab Report AI-Assisted Feedback Tool

A project to help university instructors understand and review English lab reports. The pilot focuses on one course, one report type, and DOCX files. It helps instructors inspect report structure, locate source evidence, review rubric-aligned suggestions, and prepare feedback.

## Project Documentation

- [Project plan and design brief](PROJECT_BRIEF.md): product scope, three-column review workspace, report map types, pilot data analysis, model-use constraints, privacy principles, and rollout plan.

## Core Workflow

Upload a DOCX → parse the document and assign paragraph IDs → generate a report outline and argument map → produce evidence-linked candidate suggestions against the current assignment rubric → instructor review, editing, and confirmation → export feedback.

## Design Boundaries

AI provides reviewable drafts and candidate feedback only. Report maps are not grading decisions. Suggestions without source evidence require instructor verification. Instructors control final scores, feedback, and any student-facing communication. Results from Turnitin or similar services are shown as separate reference material and do not automatically establish academic misconduct.

The project is currently in the pilot planning and interactive prototyping stage. The API integration, DOCX parsing, formal grading, and feedback delivery have not been implemented.
