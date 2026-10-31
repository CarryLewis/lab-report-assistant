# Two rubric-processing methods

Decision: 29 October 2026. Both methods remain available in the assignment editor.

## Code version

`rubric_import.parse_source` retains deterministic local text parsing. It recognizes
explicit criterion maxima in supported formats and reports unresolved input. The
editor uses the existing import endpoint and preserves the structured preview.
Parsing needs no model connection. Subsequent report review retains the existing
`writing-review-v2` feedback prompt and teacher-entered scores; code parsing does
not imply that the existing report-feedback service runs offline.

Saved rubrics record `processing_mode: code` and `processor_version: regex-v1`.
Older rubrics without a mode are treated as code-version rubrics. They are never
silently upgraded to AI interpretation or AI scores.

## AI analysis version

The teacher freely writes or imports the original rubric, then explicitly clicks
“让 AI 理解”. `/api/pilot/rubric-understand` sends the rubric and current assignment
context to the configured DeepSeek service. Typing, reopening and saving an
unchanged interpretation do not trigger model calls. AI failures do not silently
fall back to code parsing.

`rubric_ai.py` understands points, weights, levels, holistic criteria, qualitative
requirements and special rules. The server validates exact source quotations,
unique IDs, numeric bounds and arithmetic. Weights with an explicit total preserve
that scale; weight-only rubrics retain a percentage scale. Missing or contradictory
requirements remain unresolved rather than receiving invented scores or weights.

The editable understanding preserves source text separately, original level
wording, special-rule scope/caps, questions, model, prompt version and context
fingerprint. Changing rubric text, assignment type or instructions invalidates the
interpretation. Saving requires an internally consistent scoring scale; incomplete
interpretations and their original text can be stored as local drafts.

Report analysis requests one candidate score per criterion, with a rationale,
locatable report quotations, explicit uncertainty and any special-rule adjustments.
`rubric_scoring.py` checks coverage, ranges, adjustment arithmetic/direction and
report-wide explicit caps. Unknown scores are null, never zero. A partial result
has no complete suggested total. Unreadable visual material suspends numeric
scores for teacher review. These checks verify structure and evidence location;
they do not establish that a model's academic judgment is correct.

Candidate scores are stored under `analysis.score_suggestions`, separately from
teacher scores. The teacher can adopt individual scores or fill only blank fields.
No background process replaces teacher scores. Existing AI-version reports can
request new score suggestions without replacing their feedback decisions or notes.
Final teacher confirmation and existing export requirements remain in place.

## Retention and switching

The mode selector retains each method's current preview while source/context stay
unchanged. Code and AI drafts are saved independently. Copying a saved assignment
or reusing a standard preserves its method and complete AI interpretation.
Assignment revisions and imported-report snapshots retain the selected method;
changing methods on an assignment affects later imports only.

## Validation

Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` and each
`tests/test_*.js` with Node. Regression coverage includes natural-language routing,
scale preservation, source evidence, deductions, unresolved drafts, mode isolation,
old report snapshots, stale model responses and preservation of teacher scores.
Provider responses in automated tests are simulated; no live-model quality claim
is made. Browser acceptance remains pending because local test-service startup
could not complete automatic approval review in this session.
