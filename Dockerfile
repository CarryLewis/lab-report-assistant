FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py pilot_backend.py rubric_import.py citation_core.py index.html review-links.js citation-verification.js pilot.html pilot.css pilot-export.css pilot.js pilot-citations.js assignment-editor.js teacher-shell.js teacher-settings.css lab_report_rubric.default.json custom_rubric.template.json ./
COPY examples ./examples
ENV LABWISE_HOST=0.0.0.0 LABWISE_PORT=8000 LABWISE_DATA_DIR=/data
RUN useradd --uid 10001 --create-home labwise && mkdir /data && chown labwise /data
USER labwise
EXPOSE 8000
CMD ["python", "server.py"]
