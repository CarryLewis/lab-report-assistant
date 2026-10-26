"""Persist teacher review checkpoints independently of AI jobs and report revisions."""
import json
from datetime import datetime, timezone


def init_schema(c):
    c.execute('CREATE TABLE IF NOT EXISTS review_progress (report_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, last_opened TEXT NOT NULL, last_saved TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS review_order (position INTEGER PRIMARY KEY AUTOINCREMENT, report_id TEXT UNIQUE NOT NULL)')
    for row in c.execute('SELECT id FROM reports ORDER BY rowid').fetchall():
        register(c, row['id'])
    c.execute('CREATE TABLE IF NOT EXISTS review_sessions (assignment_id TEXT PRIMARY KEY, report_id TEXT NOT NULL, updated TEXT NOT NULL)')


def register(c, report_id):
    c.execute('INSERT OR IGNORE INTO review_order (report_id) VALUES (?)', (report_id,))


def grading_state(report, progress=None):
    if report.get('confirmed'):
        return 'completed'
    fields = ('notes', 'feedback', 'scores', 'reviews', 'annotations', 'teacher_summary', 'map_edits')
    return 'in_progress' if progress or any(report.get(key) for key in fields) else 'not_started'


def checkpoint(c, report, saved=False):
    if report.get('archived'):
        raise ValueError('此报告已归档，请先恢复后再批改。')
    stamp = datetime.now(timezone.utc).isoformat()
    if not report.get('confirmed') or saved:
        c.execute('INSERT INTO review_progress VALUES (?,?,?,?) ON CONFLICT(report_id) DO UPDATE SET last_opened=excluded.last_opened, last_saved=COALESCE(excluded.last_saved,review_progress.last_saved)',
                  (report['id'], stamp, stamp, stamp if saved else None))
        c.execute('INSERT INTO review_sessions VALUES (?,?,?) ON CONFLICT(assignment_id) DO UPDATE SET report_id=excluded.report_id, updated=excluded.updated',
                  (report['assignment']['id'], report['id'], stamp))
    return annotate(c, report)


def annotate(c, report):
    progress = c.execute('SELECT * FROM review_progress WHERE report_id=?', (report['id'],)).fetchone()
    return {**report, 'grading_state': grading_state(report, progress), 'review_progress': dict(progress) if progress else None}


def summaries(c):
    progress = {row['report_id']: dict(row) for row in c.execute('SELECT * FROM review_progress')}
    result = []
    for row in c.execute('SELECT q.position AS import_order,r.payload FROM reports r LEFT JOIN review_order q ON q.report_id=r.id ORDER BY q.position,r.id'):
        report = json.loads(row['payload'])
        if report.get('archived') or report.get('sample'):
            continue
        result.append({**{key: report.get(key) for key in ('id', 'filename', 'status', 'updated')},
                       'assignment_title': report['assignment']['title'], 'assignment_id': report['assignment']['id'],
                       'sample': False, 'confirmed': report.get('confirmed', False), 'student_alias': report.get('student_alias', ''),
                       'auto_analysis': report.get('auto_analysis'), 'has_ai_result': (report.get('analysis') or {}).get('mode') == 'deepseek',
                       'grading_state': grading_state(report, progress.get(report['id'])),
                       'review_progress': progress.get(report['id']), 'import_order': row['import_order']})
    return result


def continue_assignment(c, assignment_id):
    """Resume the last unfinished report, then other drafts, then import order."""
    candidates = [row for row in summaries(c) if row['assignment_id'] == assignment_id and not row['confirmed']]
    if not candidates:
        return {'report': None, 'complete': True}
    session = c.execute('SELECT report_id FROM review_sessions WHERE assignment_id=?', (assignment_id,)).fetchone()
    resume = next((r for r in candidates if session and r['id'] == session['report_id']), None)
    if not resume:
        drafts = [r for r in candidates if r['grading_state'] == 'in_progress']
        resume = max(drafts, key=lambda r: (r['review_progress'] or {}).get('last_opened', '')) if drafts else candidates[0]
    report = json.loads(c.execute('SELECT payload FROM reports WHERE id=?', (resume['id'],)).fetchone()['payload'])
    return {'report': checkpoint(c, report), 'complete': False, 'resumed': resume['grading_state'] == 'in_progress'}
