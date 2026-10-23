# Teacher Pilot Preview

Run `python3 server.py` and open http://127.0.0.1:8000/.
On macOS, double-click `start.command` and use http://127.0.0.1:8001/.
Keep the terminal open while previewing the app.

The teacher dashboard is the single product interface. It contains task summaries,
review tasks and the original three-column review workspace. `/pilot.html` redirects
to this dashboard. The earlier separate runnable interface is retired.

Open **Assignments and grading criteria** to enter an assignment title and
instructions, then upload a Word (.docx) or text-based PDF rubric, or paste its text.
The app extracts explicit criterion maxima and shows a readable preview. It asks
for clarification when scores are missing or the totals conflict, without guessing.
Saved assignments can be reopened and edited from the right-hand library.
Existing reports retain their original grading-criteria snapshots.

The review workspace continues to display interactive sample content. Its upload
selection does not yet replace that sample report with a real report. Assignment
settings use the local backend and persist in `.labwise/pilot.sqlite3`.

Run `python3 -m unittest discover -s tests -p 'test_*.py'` for validation. Word text
extraction uses the Python standard library. PDF text extraction uses pypdf from
`requirements.txt`; scanned PDFs require prior OCR.

This is a local teacher pilot. There is no public deployment or student delivery.
Data and secrets are excluded from the distributable package.
