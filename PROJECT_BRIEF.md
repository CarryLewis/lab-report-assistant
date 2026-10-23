# Lab Report AI-Assisted Feedback Tool

## Project Definition

This project is an English lab-report comprehension and feedback assistant for university instructors in China. Based on assignment instructions and a grading rubric, it helps instructors understand what a report says, inspect its argument structure and source evidence, and review and edit candidate feedback. The system supports instructor judgment and does not make final grading decisions.

## First Demo

The first version validates one complete instructor workflow:

> Upload a DOCX report → build a structured understanding of the report → analyze it against the rubric → locate source evidence → instructor edits and confirms → export feedback.

The pilot is limited to one course, one lab-report type, and parseable DOCX files. The goal is to help instructors understand English reports faster, inspect the basis for suggestions, and prepare their own final feedback.

## Core Experience

The review workspace is organized around four areas:

- **Report structure view:** Show sections, the main line of argument, and a Chinese overview to help instructors understand the report quickly.
- **English source and evidence navigation:** Let each suggestion jump to the relevant paragraph or short quotation.
- **Rubric feedback cards:** Show strengths, issues, missing elements, source evidence, and the rationale for each suggestion by rubric dimension.
- **Instructor review area:** Let instructors edit, accept, or reject suggestions and confirm final feedback.
- **Citation verification:** Link in-text citations to reference entries, verify bibliographic fields against scholarly metadata, and show claim-to-source evidence for instructor review. A metadata match never proves that the cited work supports the student's claim.

## Review Workspace Design Rationale

The review workspace uses three columns: report navigation on the left, the English source and evidence in the center, and instructor analysis, rubric review, and feedback drafting on the right. The entry page keeps two simple options—upload a DOCX or open a sample report—for preview and future integration testing.

The left-side report map provides two complementary views:

- **Report outline:** Organize the document using its actual section hierarchy and show section topics and key content, so instructors can confirm the report structure quickly.
- **Argument map:** Summarize the report's main claim, supporting claims, relationships between claims, and potential issues or missing information. Each node should link to source paragraphs.

Both views are AI-generated drafts for understanding. Instructors can switch views, revise the content, and verify it. Neither view is itself a grading result.

The right-side review and notes area includes a report overview, rubric-dimension suggestions, source evidence, instructor accept/edit/reject actions, grading rationale, private review notes, and final student feedback. Suggested wording may draw on authorized course feedback examples and instructor grading rationales. The system should retain each example's source, applicable rubric dimension, and evidence paragraph for review. Only instructor-confirmed feedback becomes deliverable.

Turnitin and similar external detection services are future integration points. Their availability depends on institutional authorization, product interfaces, and data-governance requirements. Results should be displayed as a separate evidence source and must not replace instructor judgment or automatically establish misconduct based on a similarity score or AI-detection result. An instructor must review and explicitly confirm feedback before it is sent to a student.

Report maps and outline trees support navigation and comprehension; they are not independent scoring results.

## AI Role and Boundaries

AI interprets English reports, extracts structure, proposes rubric-aligned suggestions linked to source evidence, and explains its rationale in clear Chinese.

Instructors decide whether suggestions are valid, edit the feedback, and determine final grades. Any conclusion without locatable source evidence must be marked for instructor verification and cannot serve as a definitive grading basis.

## End-to-End Constraints on Large Language Model Use

### General Principles

- The model generates reviewable comprehension results and candidate feedback only. It must not submit grades, determine academic misconduct, contact students, or perform write actions in external systems.
- The model may use only the current assignment instructions, current rubric, current report text, and explicitly authorized feedback examples. Other students' reports must not be included as implicit context for the current report.
- Split parsing, structure extraction, argument analysis, rubric suggestions, and feedback editing into separate tasks. Each task receives only the minimum data needed.
- Treat model output as untrusted data. Validate its format, fields, evidence paragraphs, and business rules before displaying it.
- Never expose the DeepSeek API key in the browser. Call the model from a server that enforces course, task, and user permissions.

### Stage-by-Stage Constraints

1. **Upload and parsing:** Accept only DOCX files supported by the pilot. Extract body text, headings, and tables, and assign immutable paragraph IDs. Stop and notify the instructor if parsing fails, the document is empty, or text extraction is abnormal; do not let the model guess. Isolate source files and parsed text by course permissions.
2. **Assignment and rubric assembly:** The server provides versioned snapshots of the current assignment instructions and rubric from course configuration. The model must not invent rubric dimensions, point values, course policy, or experimental facts that were not provided.
3. **Report-outline generation:** Output ordered sections, heading provenance, paragraph IDs, and brief summaries only. Distinguish headings that appear in the document from inferred sections; label inferences and never present them as source headings.
4. **Argument-map generation:** Each node includes a claim or issue type, supporting paragraph IDs, and a confidence/review state. Mark relationships or issues without direct evidence as requiring instructor verification. Do not interpret missing information as proof of student error.
5. **Rubric candidate suggestions:** Evaluate one rubric dimension at a time. Each suggestion must include the dimension ID, criterion, candidate performance description, source paragraph IDs, rationale, suggested feedback, and a verification flag. Do not state a definitive conclusion without valid evidence and rubric mapping. Only the instructor enters or confirms scores.
6. **Feedback-example retrieval and generation:** Retrieve only authorized, de-identified instructor examples that match the current course and rubric scope. Use them as wording references, not as sources of facts. Ground the generated feedback in the current report, never copy facts, scores, or conclusions about another student, and retain retrieved example IDs for traceability.
7. **Instructor review and export:** Mark all suggestions as drafts initially. The instructor performs acceptance, editing, rejection, scoring, and final feedback confirmation. Export is allowed only after explicit instructor confirmation. Any future student-facing delivery requires a separate confirmation action.

### Output Contract and Validation

Require a fixed JSON schema. The server validates required fields, enum values, length limits, whether paragraph IDs exist, whether rubric dimensions belong to the current assignment, and whether quotations can be located in the source. Handle refusals, empty responses, JSON parse failures, truncation, timeouts, and API errors separately. If a limited number of retries fail, preserve the source and show a recoverable error; never present incomplete output as a successful result.

For traceability, each generated object should include fields such as task_type, schema_version, model_id, prompt_version, rubric_version, source_paragraph_ids, generated_at, and review_status. Unless calibrated, confidence is only a model-provided signal. Do not present it as a validated probability or use it as an automatic grading threshold.

### Prompt Injection and Data Isolation

Treat report text, quotations, filenames, and retrieved feedback examples as untrusted input. System instructions must tell the model to analyze instruction-like text in those materials instead of following it, and not to disclose data, change grading criteria, or call tools based on it. Do not enable arbitrary tool calls for analysis. The model has no access to other courses, student records, the public internet, or secrets. The server constructs each request from the current session and verifies course and assignment ownership for every object.

### Evaluation, Versioning, and Rollback

Build a fixed evaluation set verified by instructors. Cover section structure, claim extraction, issue detection, evidence location, rubric alignment, feedback usefulness, and output validity. Run regression evaluations before changing the model, prompt, parser, or rubric mapping; do not release changes that fail agreed thresholds. Record model and prompt versions plus necessary quality metrics, and support rollback to the last stable version.

Monitor evidence errors, unsupported-suggestion rates, reasons for major instructor edits or rejections, parsing failures, and response failures. Do not use acceptance rate as the sole quality measure.

### Privacy and External Services

Before sending data to DeepSeek or another external service, confirm institutional requirements for data categories, purpose, storage and retention, service region, authorization, and contracts. Prefer sending only necessary de-identified text; exclude names, student IDs, and irrelevant metadata. Keep operational logs to the minimum necessary and do not log complete reports or API keys. Store and present Turnitin or similar results as a separate source, labeled with origin and time; do not convert them into automatic misconduct or grading decisions.

## Data Use Principles

- Use historical reports, instructor grading rationales, and rubrics to establish grading guidance, representative examples, and evaluation criteria.
- Start with authorized, de-identified samples suitable for the pilot.
- Isolate reports, parsed text, analysis results, and instructor feedback by course and permission.
- Analyze a report using only the assignment instructions and rubric needed for that assignment. Do not use historical student work as context for another student's analysis.
- Confirm institutional requirements for processing, storage, retention, and external services before the pilot.

## Pilot Data Preparation and Analysis

The first pilot uses data to evaluate workflow quality and improve suggestions. It does not use pilot data directly to train a model or automate grading.

### Data Preparation

Limit the pilot to one course, one assignment, and one rubric. Associate each de-identified sample with assignment instructions, rubric version, parsed report text, paragraph IDs, the instructor's original score and rationale, and final feedback. Store student identity separately from evaluation data and retain only fields needed for the pilot. Confirm sample authorization, access scope, retention period, and external-service conditions before processing.

### Instructor Reference Annotations

Instructors annotate scores, strengths, issues, evidence paragraphs, feedback suggestions, and items requiring verification for each rubric dimension. If multiple instructors participate, record both agreement and disagreement rather than collapsing differences into a single "correct answer." Discuss disagreements to clarify rubric boundaries and situations requiring human judgment.

### Quality and Usability Evaluation

- **Report outline:** Check section identification, ordering, omissions, and whether summaries reflect the source.
- **Argument map:** Check the accuracy and evidence for the main claim, supporting claims, argument relationships, and identified issues.
- **Rubric suggestions:** Check dimension matching, criterion alignment, evidence location, rationale quality, and feedback usefulness.
- **Instructor workflow:** Record acceptance, edits, rejection reasons, grading time, evidence-search time, and instructor ratings.

Use a small comparison involving the same or similarly difficult reports to measure time, feedback completeness, evidence accuracy, and instructor experience with and without the system. Treat acceptance rate as a behavioral signal, not a measure of correctness by itself; combine it with instructor audits and error analysis. Produce three pilot deliverables: a de-identified sample set, instructor annotations and disagreement records, and a pilot quality evaluation report.

### Instructor Feedback Corpus

Organize authorized historical comments by rubric dimension and feedback purpose. Use them as retrieval examples to support consistent wording and teaching focus. Retain each example's source and applicable scope. The model uses examples only as wording references and must generate feedback grounded in the current report; it must not copy another sample's facts, score, or conclusion. Evaluate retrieval-augmented generation during the pilot before considering fine-tuning.

### External Detection Results

Store results from Turnitin or similar tools separately with their source, timestamp, and interpretation scope. Present them as material for instructor review, separate from rubric evaluation. Do not use similarity or AI-detection results alone to automatically conclude misconduct or generate punitive feedback.

## Next Steps

1. Select one course, assignment, and rubric.
2. Prepare a small set of historical samples and confirm instructors' real grading steps, common issues, and feedback style.
3. Build and test the first end-to-end demo with a small group of instructors using historical reports.
4. Use instructor acceptance, edits, rejection, and evidence-accuracy ratings to guide improvements.
5. Expand courses, report types, user scale, deployment options, and machine-learning capabilities only after the pilot is stable.

## Deferred from the First Demo

The following are outside the first demo scope:

- Automatically assigning final grades.
- Supporting every course and lab-report type.
- Complex PDFs, scanned documents, OCR, handwriting, and complex equations.
- A student-facing application, real-time multi-user collaboration, and cross-course analytics.
- Local or campus-hosted model deployment.
- Training or fine-tuning before stable annotations and evaluation results are available.

## Product Decision Principle

All future functionality must support this core goal:

> Help instructors understand English lab reports faster and produce feedback they can review, edit, confirm, and ground in visible source evidence and the rubric.

If a feature does not improve comprehension, evidence traceability, rubric alignment, or instructor review, validate its value before including it in development.

