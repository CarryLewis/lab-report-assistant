"""Durable single-worker automatic report analysis. No model calls in upload requests."""
import json
import os
import threading
import uuid

_wake = threading.Event()
_thread = None
_start_lock = threading.Lock()


def init_schema(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS analysis_jobs (
        report_id TEXT PRIMARY KEY, state TEXT NOT NULL, run_id TEXT NOT NULL,
        created TEXT NOT NULL, updated TEXT NOT NULL, error TEXT, attempts INTEGER NOT NULL DEFAULT 0, owner_pid INTEGER)''')
    if 'owner_pid' not in {row['name'] for row in connection.execute('PRAGMA table_info(analysis_jobs)')}:
        connection.execute('ALTER TABLE analysis_jobs ADD COLUMN owner_pid INTEGER')


def is_live_job(connection, report_id):
    row=connection.execute("SELECT owner_pid,state FROM analysis_jobs WHERE report_id=?",(report_id,)).fetchone()
    if not row or row['state']!='running' or not row['owner_pid']:
        return False
    try:
        os.kill(row['owner_pid'],0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def enqueue(connection, report, retry=False):
    import pilot_backend as backend
    if report.get('sample') or report.get('archived') or report.get('confirmed'):
        return False
    if (report.get('analysis') or {}).get('mode') == 'deepseek':
        return False
    current=connection.execute('SELECT * FROM analysis_jobs WHERE report_id=?',(report['id'],)).fetchone()
    if current and current['state']!='done' and not (retry and current['state'] in ('failed','blocked')):
        return False
    state='queued' if backend.KEY else 'blocked'
    reason=None if state=='queued' else '尚未配置 AI 密钥；在设置中连接后会自动继续。'
    stamp=backend.now();run_id=uuid.uuid4().hex
    if current:
        connection.execute('UPDATE analysis_jobs SET state=?,run_id=?,updated=?,error=? WHERE report_id=?',(state,run_id,stamp,reason,report['id']))
    else:
        connection.execute('INSERT INTO analysis_jobs (report_id,state,run_id,created,updated,error) VALUES (?,?,?,?,?,?)',(report['id'],state,run_id,stamp,stamp,reason))
    report['auto_analysis']={'state':state,'run_id':run_id,'updated':stamp,'error':reason}
    report.update(status='queued' if state=='queued' else 'waiting_key',error=reason)
    backend.persist(connection,report)
    _wake.set()
    return True


def resume_blocked(connection):
    import pilot_backend as backend
    if not backend.KEY:
        return
    rows=connection.execute("SELECT report_id FROM analysis_jobs WHERE state='blocked'").fetchall()
    for row in rows:
        report=backend.get_report(connection,row['report_id'])
        enqueue(connection,report,retry=True)
    _wake.set()


def recover(connection):
    import pilot_backend as backend
    # An interrupted provider call has an unknown outcome: require explicit retry,
    # rather than silently issuing another billable request after a process crash.
    for row in connection.execute("SELECT * FROM analysis_jobs WHERE state='running'").fetchall():
        if is_live_job(connection,row['report_id']):
            continue
        report=backend.get_report(connection,row['report_id'])
        reason='服务重启中断了 AI 分析，可在文件列表中重试。'
        report.update(status='failed',error=reason)
        report['auto_analysis']={'state':'failed','run_id':row['run_id'],'updated':backend.now(),'error':reason}
        backend.persist(connection,report)
        connection.execute("UPDATE analysis_jobs SET state='failed',error=?,updated=? WHERE report_id=?",(reason,backend.now(),report['id']))
    # Bring earlier unfinished uploads into this workflow once. Already confirmed
    # work and successful AI results never trigger another call on opening a file.
    for row in connection.execute('SELECT payload FROM reports').fetchall():
        enqueue(connection,json.loads(row['payload']))
    resume_blocked(connection)


def run_one(tls):
    import pilot_backend as backend
    with backend.db() as connection:
        connection.execute('BEGIN IMMEDIATE')
        row=connection.execute("SELECT * FROM analysis_jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
        if not row:
            return False
        report=backend.get_report(connection,row['report_id'])
        if report.get('archived') or report.get('confirmed') or (report.get('analysis') or {}).get('mode')=='deepseek':
            connection.execute("UPDATE analysis_jobs SET state='done',updated=? WHERE report_id=?",(backend.now(),report['id']))
            if report.get('status') in ('queued','waiting_key'):
                report['status']='ready' if report.get('analysis') else 'parsed'
                report['auto_analysis']={'state':'done','run_id':row['run_id'],'updated':backend.now(),'error':None}
                report['error']=None;backend.persist(connection,report)
            return True
        if report.get('status')=='analyzing':
            return False  # A separate visual or legacy analysis owns this report.
        if not backend.KEY:
            reason='尚未配置 AI 密钥；在设置中连接后会自动继续。'
            report.update(status='waiting_key',error=reason)
            report['auto_analysis']={'state':'blocked','run_id':row['run_id'],'updated':backend.now(),'error':reason}
            backend.persist(connection,report)
            connection.execute("UPDATE analysis_jobs SET state='blocked',error=?,updated=? WHERE report_id=?",(reason,backend.now(),report['id']))
            return True
        backend.snapshot(connection,report)
        report.update(status='analyzing',error=None,revision=report['revision']+1)
        report['auto_analysis']={'state':'running','run_id':row['run_id'],'updated':backend.now(),'error':None}
        backend.persist(connection,report)
        connection.execute("UPDATE analysis_jobs SET state='running',attempts=attempts+1,updated=?,owner_pid=? WHERE report_id=?",(backend.now(),os.getpid(),report['id']))
        config=json.loads(connection.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0])
        token=row['run_id']
    try:
        output=backend.analyze(report,'deepseek',config,tls)
        failure=None
    except Exception as error:
        output=None
        failure=str(error) if isinstance(error,ValueError) else 'AI 分析暂未完成，请在文件列表中重试。'
    with backend.db() as connection:
        connection.execute('BEGIN IMMEDIATE')
        current=connection.execute('SELECT * FROM analysis_jobs WHERE report_id=?',(report['id'],)).fetchone()
        if not current or current['run_id']!=token or current['state']!='running':
            return True
        saved=backend.get_report(connection,report['id'])
        # Do not replace teacher fields, private notes, scores or visual reviews.
        if output is not None:
            saved.update(analysis=output,status='ready',error=None)
            state='done'
        else:
            saved.update(status='failed',error=failure)
            state='failed'
        saved.update(revision=saved['revision']+1,confirmed=False)
        saved['auto_analysis']={'state':state,'run_id':token,'updated':backend.now(),'error':failure}
        backend.persist(connection,saved)
        connection.execute('UPDATE analysis_jobs SET state=?,error=?,updated=? WHERE report_id=?',(state,failure,backend.now(),report['id']))
    return True


def start(tls):
    global _thread
    with _start_lock:
        if _thread and _thread.is_alive():
            return
        def worker():
            while True:
                try:
                    if run_one(tls):
                        continue
                except Exception:
                    # Leave durable state intact; recover at the next process start.
                    pass
                _wake.wait(3);_wake.clear()
        _thread=threading.Thread(target=worker,name='labwise-auto-analysis',daemon=True)
        _thread.start()
