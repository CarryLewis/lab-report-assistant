# Complex Word Preview in 1.2.1

Updated 24 October 2026. Applies to DOCX preview, not legacy binary DOC files.

## Failure and resolution

The reported document contained a linked OLE data source in a chart relationship.
The previous converter rejected the entire document whenever such a relationship
was found. The preview now creates a temporary derivative, removes external
resource dependencies and uses the embedded images, cached chart values and field
results already present. The uploaded original and source hash are unchanged.

Drawing links with no embedded image receive a local gray placeholder. Unsupported
linked objects or inserted external content are omitted from the derivative with
an explicit notice. Ordinary web hyperlinks remain links. XML entity definitions
and oversized or invalid packages are rejected. Embedded SVG external references
and active content are removed from the preview copy. Macro execution and link,
field and chart updates are disabled in an isolated conversion profile.

The converter configuration follows LibreOffice's documented Writer update options:
[Writer configuration schema](https://github.com/LibreOffice/core/blob/master/officecfg/registry/schema/org/openoffice/Office/Writer.xcs).
These measures preserve offline rendering rather than downloading unknown content.
They are not a claim that every possible Office object has a faithful representation.

## Response and display

POST /api/pilot/document-preview returns either:

- application/pdf, preview_mode=paged, a base64 file and a warnings list.
- text/html, preview_mode=readable, escaped HTML and warnings when pagination is
  unavailable or conversion fails/times out.

The readable fallback supports paragraphs, common emphasis, table text, formula
text and embedded PNG/JPEG/GIF images. It is displayed in a sandboxed frame with
network resources and scripts blocked. It does not reproduce exact pagination,
floating shapes, every chart or Word's complete layout. Original-page anchoring
and annotation are unavailable in that fallback, and the UI says so.

The PDF reader requires an absolutely positioned scrolling container. The toolbar
height is measured so wrapped controls do not cover the page. A mistakenly
HTML-filled main stylesheet was restored from the saved 1.2.1 CSS baseline.

## Observed result

The originally failing uploaded DOCX converted to a seven-page PDF. After the
service update, the browser displayed page 1 of 7 with rendered report content.
No grading, report text or original source file was changed by this repair.
The live service was restarted to load Python changes; process-memory API keys
may need to be re-entered if not supplied through the deployment environment.
