"""Consistent local backups; restore into a separate copy, never over live work."""
import base64
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import sqlite3
import sys
import tempfile
import uuid
import zipfile

LIMIT = 64 * 1024 * 1024
EXPANDED_LIMIT = 256 * 1024 * 1024
ASSET = re.compile(r'(?:sources/[A-Za-z0-9_-]+\.bin|visuals/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+\.png|scan_previews/[A-Za-z0-9_-]+\.pdf)\Z')


def dispatch(method, path, body):
    import pilot_backend as backend
    if method == 'GET' and path == '/api/pilot/data-info':
        return {'directory': str(backend.DATA.resolve()), 'backup_limit_mb': LIMIT // 1024**2,
                'restore_mode': 'separate-copy', 'credentials_included': False}
    if method == 'POST' and path == '/api/pilot/backup':
        return create()
    if method == 'POST' and path == '/api/pilot/restore-backup':
        return restore(body.get('file', ''))
    raise LookupError('未找到数据操作。')


def create():
    import pilot_backend as backend
    with tempfile.TemporaryDirectory(prefix='labwise-backup-') as work:
        database = Path(work) / 'pilot.sqlite3'
        with backend.db() as connection, closing(sqlite3.connect(database)) as target:
            connection.backup(target)
        # A test result is tied to a local credential, which is never backed up.
        with closing(sqlite3.connect(database)) as connection, connection:
            config = json.loads(connection.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0])
            config.pop('_connection_key_hash', None)
            config.pop('connection_test', None)
            connection.execute('UPDATE settings SET payload=? WHERE id=1', (json.dumps(config),))
            reports = [json.loads(row[0]) for row in connection.execute('SELECT payload FROM reports')]
            revisions = [json.loads(row[0]) for row in connection.execute('SELECT payload FROM revisions')]
        files = {'pilot.sqlite3': database}
        # Source files are immutable after import; use the DB snapshot to select
        # only the files it refers to, rather than copying an active directory.
        for report in reports + revisions:
            rid = report['id']
            source = f'sources/{rid}.bin'
            if report.get('source_filename'):
                file = backend.DATA / source
                if not ASSET.fullmatch(source) or not file.is_file() or file.is_symlink():
                    raise ValueError('原始报告文件缺失，未生成不完整备份。')
                if hashlib.sha256(file.read_bytes()).hexdigest() != report.get('source_sha256'):
                    raise ValueError('原始报告校验失败，请先检查资料。')
                files[source] = file
            folder = backend.DATA / 'visuals' / rid
            if re.fullmatch(r'[A-Za-z0-9_-]+', rid) and folder.is_dir() and not folder.is_symlink():
                for file in folder.glob('*.png'):
                    name = file.relative_to(backend.DATA).as_posix()
                    if ASSET.fullmatch(name) and not file.is_symlink():
                        files[name] = file
            preview = f'scan_previews/{rid}.pdf'
            file = backend.DATA / preview
            if ASSET.fullmatch(preview) and file.is_file() and not file.is_symlink():
                files[preview] = file
        if sum(file.stat().st_size for file in files.values()) > EXPANDED_LIMIT:
            raise ValueError('资料超过本机备份工具的 256 MB 展开限额，请先关闭应用并复制整个数据目录备份。')
        output = io.BytesIO()
        manifest = {'format': 'labwise-backup.v1', 'created_at': backend.now(), 'files': {}}
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, file in files.items():
                raw = file.read_bytes()
                manifest['files'][name] = hashlib.sha256(raw).hexdigest()
                archive.writestr(name, raw)
            archive.writestr('manifest.json', json.dumps(manifest))
        raw = output.getvalue()
        if len(raw) > LIMIT:
            raise ValueError('备份超过 64 MB，请关闭应用并复制整个数据目录备份。')
        return {'filename': 'Labwise-backup-' + backend.now()[:10] + '.zip',
                'content_type': 'application/zip', 'content': base64.b64encode(raw).decode(),
                'reports': len(reports), 'credentials_included': False}


def restore(encoded):
    import pilot_backend as backend
    if not isinstance(encoded, str) or len(encoded) > (LIMIT * 4 // 3 + 4):
        raise ValueError('备份文件不能超过 64 MB。')
    try:
        raw = base64.b64decode(encoded, validate=True)
        archive = zipfile.ZipFile(io.BytesIO(raw))
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) > 20000 or len(names) != len(set(names)) or sum(e.file_size for e in entries) > EXPANDED_LIMIT:
            raise ValueError()
        if 'manifest.json' not in names or 'pilot.sqlite3' not in names:
            raise ValueError()
        for entry in entries:
            name = entry.filename
            if name not in ('manifest.json', 'pilot.sqlite3') and not ASSET.fullmatch(name):
                raise ValueError()
            if '..' in PurePosixPath(name).parts or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError()
        manifest = json.loads(archive.read('manifest.json'))
        if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), dict):
            raise ValueError()
        if manifest.get('format') != 'labwise-backup.v1' or set(manifest['files']) != set(names) - {'manifest.json'}:
            raise ValueError()
        parent = backend.DATA.resolve().parent
        staging = Path(tempfile.mkdtemp(prefix='.labwise-restore-', dir=parent))
        try:
            for name, digest in manifest['files'].items():
                content = archive.read(name)
                if hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError()
                file = staging / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(content)
            with closing(sqlite3.connect(staging / 'pilot.sqlite3')) as connection, connection:
                if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError()
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'reports', 'assignments', 'settings', 'revisions', 'analysis_jobs'} <= tables:
                    raise ValueError()
                # Verify each saved report and referenced source before making
                # this a usable copy. Never trust paths supplied by an archive.
                for row in connection.execute('SELECT payload FROM reports UNION ALL SELECT payload FROM revisions'):
                    report = json.loads(row[0])
                    if not isinstance(report, dict) or not isinstance(report.get('id'), str):
                        raise ValueError()
                    if report.get('source_filename'):
                        name = f"sources/{report['id']}.bin"
                        if name not in manifest['files'] or manifest['files'][name] != report.get('source_sha256'):
                            raise ValueError()
                config = json.loads(connection.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0])
                config.pop('_connection_key_hash', None)
                config.pop('connection_test', None)
                connection.execute('UPDATE settings SET payload=? WHERE id=1', (json.dumps(config),))
                # Interrupted jobs must not inherit a live PID or trigger an
                # unexpected billable request on opening the recovered copy.
                connection.execute("UPDATE analysis_jobs SET state='failed',owner_pid=NULL,error='从备份恢复，请核对后重试分析。' WHERE state IN ('queued','running')")
                for row in connection.execute('SELECT id,payload FROM reports').fetchall():
                    report = json.loads(row[1])
                    if report.get('status') in ('queued', 'analyzing'):
                        report.update(status='failed', error='从备份恢复，请核对后重试分析。')
                        report['auto_analysis'] = {'state': 'failed', 'error': report['error']}
                        connection.execute('UPDATE reports SET payload=? WHERE id=?', (json.dumps(report), row[0]))
            destination = parent / ('Labwise-restored-' + uuid.uuid4().hex[:12])
            # Prepare every output before publishing the recovery directory.
            launcher = staging / '启动恢复副本.command'
            command = shlex.quote(sys.executable)
            if not getattr(sys, 'frozen', False):
                command += ' server.py'
            launcher.write_text('#!/bin/sh\ncd ' + shlex.quote(str(backend.ROOT)) + ' || exit 1\n'
                                'unset DEEPSEEK_API_KEY\nexport LABWISE_DATA_DIR=' + shlex.quote(str(destination)) + '\n'
                                'export LABWISE_PORT=8002\n' + command + '\n', encoding='utf-8')
            os.chmod(launcher, 0o700)
            (staging / '恢复说明.txt').write_text('这是独立恢复副本，原工作区没有被替换。关闭当前应用后，macOS 可双击同目录的“启动恢复副本.command”，再打开 http://127.0.0.1:8002/ 。如端口已被占用，请先关闭此前的恢复副本。请重新配置分析密钥。\n其他系统请由维护者将 LABWISE_DATA_DIR 指向本目录，并使用独立端口启动程序。\n升级程序前保留此数据目录和备份 ZIP；不要覆盖资料目录。', encoding='utf-8')
            staging.rename(destination)
            launcher = destination / launcher.name
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {'directory': str(destination), 'launcher': str(launcher), 'url': 'http://127.0.0.1:8002/',
                'mode': 'separate-copy', 'original_unchanged': True}
    except (ValueError, KeyError, TypeError, zipfile.BadZipFile, sqlite3.DatabaseError, UnicodeDecodeError, RuntimeError, EOFError):
        raise ValueError('备份格式、完整性或资料校验失败；当前工作区未改变。')
