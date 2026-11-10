FROM python:3.14-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY document_preview.py document-viewer.js document-viewer.css turnitin-bridge.js turnitin-bridge.css server.py pilot_backend.py rubric_import.py citation_core.py index.html review-links.js citation-verification.js pilot.html pilot.css pilot-export.css pilot.js pilot-citations.js assignment-editor.js teacher-shell.js teacher-settings.css teacher-modules.js teacher-modules.css workspace-resize.js workspace-resize.css lab_report_rubric.default.json custom_rubric.template.json ./
COPY examples ./examples
COPY vendor ./vendor
COPY word_source.py word_export.py pdf_export.py pdf-export.js pdf-export.css word-reader.html word-reader.js word-reader.css auto_analysis.py review_progress.py visual_review.py visual_discovery.py visual-inventory.js teacher-live.js teacher-live.css original-reader.html original-reader.mjs ./
COPY i18n.js i18n-en.js i18n-init.js i18n.css app_paths.py local_backup.py user-support.js user-support.css VERSION RELEASE_CHANNEL STABLE_VERSION ./
COPY rubric_ai.py rubric_scoring.py writing_profiles.py review_guidance.py word_review.py ./
COPY evaluation_language.py design-system.css review-layout.css ./
COPY cloud_backup.py cloud-backup.js cloud-backup.css ./
COPY corpus/writing_profiles.json ./corpus/
ENV LABWISE_HOST=0.0.0.0 LABWISE_PORT=8000 LABWISE_DATA_DIR=/data
RUN useradd --uid 10001 --create-home labwise && mkdir /data && chown labwise /data
USER labwise
EXPOSE 8000
CMD ["python", "server.py"]
