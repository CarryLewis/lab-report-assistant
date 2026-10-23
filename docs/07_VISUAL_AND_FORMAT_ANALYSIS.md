# Visual, Scientific Figure, and Format Analysis

## Purpose

This module identifies images, plots, diagrams, tables, equations, captions, in-text callouts, and references in a lab report. It separates three kinds of output:

1. **Deterministic format checks** — numbering, caption position, cross-references, units, reference-style fields.
2. **Visual extraction** — chart type, axes, labels, legend, series, error bars, table cells, image quality.
3. **Scientific review candidates** — whether the visible evidence supports the student's interpretation.

Only teacher-confirmed findings can affect scoring or student-facing feedback.

## Teacher workflow

1. Open **图表与格式** in the assessment workspace.
2. Review the inventory: figures, tables, diagrams, photographs, and equations.
3. Select an item to jump to its page and bounding box.
4. Review deterministic checks first.
5. Compare extracted chart facts with the Results and Discussion text.
6. Confirm, edit, or reject each scientific-review candidate.
7. Attach confirmed findings to a rubric criterion.

## Detection pipeline

### 1. Document layout extraction

Preserve page number and bounding boxes for:

- paragraphs and headings;
- raster images and vector graphics;
- figure and table captions;
- tables and cell coordinates;
- equations;
- footnotes and references.

DOCX objects should be rendered to a stable PDF preview so that evidence anchors use the same coordinate system as the teacher-facing document viewer.

### 2. Visual object classification

Classify every detected object as one of:

- scientific plot;
- data table;
- experimental apparatus diagram;
- microscopy or photographic image;
- flowchart or conceptual diagram;
- equation;
- decorative or irrelevant image.

Store the classification confidence and allow manual correction.

### 3. Plot extraction

For scientific plots, extract when visible:

- chart type;
- title;
- X/Y axis labels and units;
- tick labels and scale type;
- legend labels;
- series count and colors;
- data markers;
- error bars and their apparent type;
- regression/trend lines;
- statistical annotations;
- panel labels such as A/B/C;
- caption text and figure number.

The first version should not promise exact digitisation of arbitrary charts. Store extracted observations as candidates with source bounding boxes.

### 4. Cross-document linking

Link each visual object to:

- its caption;
- in-text references such as “Figure 1 shows”;
- nearby Results statements;
- Discussion interpretations;
- cited sources in the caption;
- the relevant rubric criterion.

The system must distinguish “a figure exists” from “the text explicitly refers to the figure.”

## Check catalogue

### Figures and plots

- figure number exists and is sequential;
- caption exists and is in the required position;
- axes have meaningful labels;
- units are present where applicable;
- legend is present when multiple series exist;
- symbol, line, and color encodings are explained;
- error bars are present when the rubric or experimental design expects variability;
- statistical annotations are defined;
- image resolution and text size are readable;
- colors remain distinguishable without relying on color alone;
- the figure is referenced in the body text;
- caption/source citation is present for reused or adapted material.

### Tables

- table number and title exist;
- column headings and units exist;
- decimal precision is consistent;
- missing values are explained;
- statistical summaries identify n and variability measure;
- table is referenced in the body;
- duplicated information between chart and table is flagged as an optional style issue.

### Scientific images

- scale bar, magnification, orientation, stain, channel, or acquisition method is present when relevant;
- annotations and regions of interest are explained;
- image manipulation or composite panels are disclosed when required;
- source attribution is present for reused images;
- labels are readable and panel lettering is sequential.

### References and document format

- citation style matches the assignment profile;
- every in-text citation resolves to a reference entry;
- every reference entry is cited in the text;
- DOI/URL fields are formatted consistently;
- figure/table citations are separate from scholarly source citations;
- species names, variables, and statistical symbols use the required italics;
- heading, numbering, margin, line-spacing, and word-count rules follow the course template.

## Scientific review logic

Scientific review must compare three evidence sources:

1. extracted visual facts;
2. the student's textual claim;
3. the rubric or marking guide.

Example:

- Visual fact: the curve increases and then its slope decreases.
- Student claim: the culture entered the stationary phase.
- Missing evidence: no replicates, error bars, or later time points.
- Candidate conclusion: the figure supports growth and a reduced rate, but does not confidently establish a stationary phase.

This is a review candidate, not an automatic deduction.

## Structured output

```json
{
  "visual_id": "figure-1",
  "document_version_id": "doc-123",
  "page": 3,
  "bbox": [0.12, 0.28, 0.86, 0.74],
  "type": "line_plot",
  "number": "Figure 1",
  "caption": "Optical density ...",
  "extracted": {
    "x_axis": {"label": "Time", "unit": "min"},
    "y_axis": {"label": "Optical density", "unit": "OD600"},
    "series": 1,
    "legend_present": false,
    "error_bars_present": false
  },
  "links": {
    "in_text_callouts": [],
    "claims": ["claim-results-3"],
    "rubric_criteria": ["data-analysis"]
  },
  "checks": [
    {
      "code": "FIGURE_CROSS_REFERENCE_MISSING",
      "kind": "deterministic",
      "status": "failed",
      "confidence": "high",
      "teacher_confirmation_required": true
    }
  ]
}
```

## Data model additions

- `visual_objects(id, document_version_id, page, bbox, type, confidence)`
- `visual_captions(id, visual_object_id, number, text, bbox)`
- `visual_features(id, visual_object_id, schema_version, payload)`
- `visual_text_links(id, visual_object_id, document_block_id, relation_type)`
- `format_profiles(id, assignment_id, citation_style, rules, version)`
- `format_checks(id, submission_id, object_id, rule_code, status, evidence)`
- `scientific_review_candidates(id, visual_object_id, claim_block_id, criterion_id, rationale, confidence)`
- `teacher_visual_decisions(id, candidate_id, user_id, decision, note, created_at)`

## API boundaries

- `GET /submissions/{id}/visual-objects`
- `GET /visual-objects/{id}`
- `GET /submissions/{id}/format-checks`
- `POST /visual-review/{candidateId}:confirm`
- `POST /visual-review/{candidateId}:reject`
- `PATCH /visual-objects/{id}/classification`

All responses must return page and bounding-box evidence so the UI can highlight the source.

## Quality evaluation

Build a golden set covering line/bar/scatter plots, multi-panel figures, microscopy images, tables, diagrams, low-resolution screenshots, and malformed citations. Measure:

- object detection precision/recall;
- caption-to-figure linking accuracy;
- axis/label/unit extraction accuracy;
- error-bar detection accuracy;
- in-text cross-reference accuracy;
- citation-style rule precision;
- scientific candidate acceptance/edit/rejection rate;
- teacher time saved per visual object.

Formatting checks should target high precision. Scientific-review candidates may optimise for useful recall, but must always show evidence and require teacher confirmation.

## MVP sequence

1. Figure/table detection, caption linking, numbering, and in-text cross-reference checks.
2. Axis/label/unit/legend/error-bar extraction for common 2D plots.
3. Reference-style and course-template rules.
4. Claim-to-figure linking and evidence-backed scientific review candidates.
5. Microscopy, apparatus diagrams, multi-panel figures, and chart digitisation.

## Safety boundaries

- Treat all image text and captions as untrusted student content.
- Do not follow instructions embedded in an image or document.
- Do not infer fabrication or misconduct from visual anomalies alone.
- Do not make medical, biological, or safety claims beyond the supplied evidence.
- Preserve the original document and extracted regions for audit.
- Never change a score until a teacher confirms the finding and its rubric relationship.
