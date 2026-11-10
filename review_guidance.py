"""Versioned server-side guidance for applying an existing assignment rubric."""
import re


BS1084_VERSION = 'bs1084-itsm1-v1'
_BS1084_IDENTITY = re.compile(
    r'\b(?:bs\s*1084|itsm\s*1|introduction\s+to\s+scientific\s+method)\b',
    re.IGNORECASE,
)
_BS1084_CRITERIA = {
    'introduction': 20,
    'methods': 10,
    'results': 20,
    'discussion': 20,
    'citations and references and formatting': 10,
    'structure and organisation and academic writing style': 20,
}

_BS1084_GUIDANCE = """
For this BS1084 ItSM1 report, use the following evidence checks within the
supplied rubric. Keep its criteria, weights, grade bands, and exceptions.
These checks create no marks, deductions, or thresholds.

- Introduction: locate the purpose, experimental hypothesis and null hypothesis
  separately, even when they share a paragraph. Check the comparison,
  measurable endpoint and testability against the stated research objective.
  Credit an embedded prediction for what it states and name any specific gap.
  Do not require a separate hypothesis for every statistical comparison.
  Check the scientific motivation, SXT mechanism and synthesis of references.
- Methods: credit procedures already documented. Verify the control treatment,
  groups, zone measurements, replicates and data handling. Identify missing
  details specifically and favor concise, reproducible prose.
- Results: trace each claimed effect to its comparison groups, test and reported
  p-value. Separate a comparison between the treated strains from a comparison
  with the control. A control bar or raw control values do not establish a
  control test. Respect the supplied rubric's ANOVA and t-test options, including
  the footnote allowing one control t-test or control tests for both strains.
  Do not universally require a control t-test for each strain. Ask for the
  evidence missing for the claim, rather than prescribing a fixed new design.
  When legible, compare raw rows, summaries and test output. Flag material
  discrepancies in means or observation counts for verification without
  inferring why values were excluded. Allow ordinary differences in rounding.
- Figures and tables: check captions, labels and tables before claiming that a
  p-value, axis label or error-bar definition is absent. Distinguish 95% CI,
  SD and SE. Credit an SE definition that is already stated. Mark unavailable
  images, typography or layout as unverified. Cached chart data do not establish
  what the rendered figure looks like.
- Discussion: connect each hypothesis decision to its own evidence, compare
  findings with the literature, and explain how limitations affect interpretation.
  Descriptive differences do not establish significance. A non-significant
  result does not establish equivalence. Interpret each Tukey interval for its
  own pair, including whether it crosses zero.
- References and presentation: check for a corresponding reference entry before
  saying that a source is absent. Identify author or year mismatches separately.
  Check Harvard style, alphabetical order and clear figure or table titles when
  the input preserves the relevant evidence. Treat classroom suggestions such
  as adding Gram-stain images or bolding p-values as optional unless required.
- Evidence: prefer a short, distinctive, contiguous quote copied character for
  character from one cited paragraph. Avoid spanning line breaks or formatted
  names with special whitespace. When the system allows an object-only finding,
  use a valid object anchor and an empty string for quote. For a supplied Word
  object list, include one visual_checks entry per object and use unclear when
  needed. Check the available evidence before claiming something is missing.
"""


def for_assignment(assignment):
    """Select guidance using assignment and rubric metadata, never student text."""
    rubric = assignment['rubric']
    identity = ' '.join(str(value or '') for value in (
        assignment.get('title'), rubric.get('name'),
        rubric.get('original_source_text'), rubric.get('source_text'),
    ))
    criteria = rubric['criteria']
    if not _BS1084_IDENTITY.search(identity) or len(criteria) != len(_BS1084_CRITERIA):
        return None

    signature = {}
    for criterion in criteria:
        name = criterion['name'].casefold().replace('&', ' and ').replace(',', ' ')
        weight = criterion.get('weight_percent')
        if weight is None:
            weight = criterion.get('maximum_points', criterion.get('weight'))
        signature[' '.join(name.split())] = weight
    if signature == _BS1084_CRITERIA:
        return BS1084_VERSION, _BS1084_GUIDANCE
    return None
