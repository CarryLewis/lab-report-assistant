# Runnable Pilot

On macOS, double-click `start.command` to start on port 8001. Keep the terminal open.
Alternatively, run `python3 server.py`, then open http://127.0.0.1:8000/pilot.html.
If port 8000 is already occupied by the old preview server, stop that process
with Ctrl+C or run `LABWISE_PORT=8001 python3 server.py` and use port 8001.
Python 3.10+ is required. Optional `pip install -r requirements.txt` supplies
an updated certificate bundle for outbound scholarly/DeepSeek requests.

1. Open the built-in fictional sample and select example analysis.
2. Review the numbered suggestions, enter all criterion scores and final feedback.
3. Save, confirm and export the UTF-8 TXT feedback. Private notes are excluded.
4. Reopen a report after restarting the server; drafts persist in SQLite.
5. Use version history to restore a prior draft. Restoring revokes confirmation.
6. Create an assignment and import `pilot-rubric.json`; review the preview before saving.
7. Upload a DOCX (up to 10 MB). Real document text is parsed locally; structure mode
   extracts headings only. AI findings require a configured DeepSeek key.

Model settings persist the selected model. The API key stays in server memory
and is never returned to the browser or stored in SQLite. Restart clears keys
entered through the UI; DEEPSEEK_API_KEY can provide a startup key.
A separate confirmation precedes sending report text to DeepSeek. An analysis
records the model, prompt version and validated source paragraph references.
Invalid evidence, truncated output and API errors leave a recoverable error.

Data lives in `.labwise/pilot.sqlite3` and is not served as a web asset. Stop the
server before copying the database for a backup. The local app is single-user,
without authentication. It binds to localhost by default and is not intended
for shared/public deployment. DOCX extraction includes table text but not original
layout, image interpretation, OCR, tracked changes or equation rendering.

Docker (when installed): `docker compose up --build`. Open the same URL. The named
volume persists data. Do not use `docker compose down -v` if you need to retain it.

DeepSeek Chat Completions reference:
https://api-docs.deepseek.com/api/create-chat-completion/
