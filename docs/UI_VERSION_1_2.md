# Labwise 1.2 — UI Baseline

## Recorded variants

Active: **1.2.1**, without Team and Calibration. Navigation is 01 Dashboard,
02 Courses and Assignments, 03 Grading Standards, 04 Review Analytics and
05 Settings and Activity. Direct navigation to the removed route returns home.

Retained: **1.2.2**, with all six original modules including Team and Calibration.
Both variants retain the same visual baseline described below. Source snapshots
and manifests are recorded in [versions](../versions/README.md). Existing local
calibration notes and user data are preserved; 1.2.2 retains the demonstration
screen rather than a production shared-review service.

Baseline date: 24 October 2026. The user-supplied screenshot of the teacher pilot
is the accepted visual and navigation reference. This decision supersedes the
later three-entry shell and editable-product replacement as the current UI.
The later designs are historical proposals, not the accepted 1.2 interface.

## Global shell

White top bar: LW / Labwise brand, teacher-pilot badge with v1.2, assignment/rubric
shortcut, usage help and teacher avatar. Dark course sidebar: BIOE 204 and course
name, six numbered destinations, course/workspace footer. Pale gray main canvas,
white bordered panels, blue actions and restrained academic marking-tool styling.

## Dashboard

Teacher greeting and semester label. Shortcuts for assignment requirements and
grading standards. Three summary cells: pending reports, second-review needs and
assignment completion. Continue-review panel on the left with document/student
labels, progress, deadlines and actions. Report import panel on the right with
DOCX/text-PDF selection and teacher-decision reminder. Demonstration totals and
tasks remain explicitly labeled as pilot examples.

## Six destinations

01 Dashboard: task summary, continue marking and report import.
02 Courses and Assignments: original assignment-name/requirements/rubric-text
editor, Word/PDF criteria import, saved assignments and readable rubric preview.
03 Grading Standards: saved standards, reference template and reuse/edit actions.
04 Team and Calibration: labeled example cases and local notes; not real shared
reviewer accounts or a collaboration service.
05 Review Analytics: actual local imported-report processing counts, excluding
sample reports; no invented score distributions.
06 Settings and Activity: original reading preferences and browser-local activity;
not institutional authentication or a formal audit service.

## Review workspace

Restore the original report/map/rubric workspace, evidence-linked suggestion cards,
numbered red/green map markers, teacher notes, original resize controls and existing
reserved Turnitin preview. Preserve its sample labels and integration boundaries.

## Rollback record

The accepted shell and original sample dashboard were restored from the retained
prototype source, with the six navigation routes reinstated. The replacement
product.js/product.css entry and its new settings/workspace were withdrawn from
the active page. Assignment type/batch panels and structured criterion builder
were removed from the accepted UI. Later replacement sources are stored only in
archive/withdrawn-editable-ui and are not part of the served UI.

Existing local data and compatible backend storage were retained to avoid losing
saved reports, assignment snapshots or notes. This is a UI rollback, not deletion
of user data or a destructive database downgrade. Earlier documents 11–13 describe
superseded proposals/implementations where they conflict with this baseline.

Future UI changes should extend this 1.2 baseline only when explicitly requested.
