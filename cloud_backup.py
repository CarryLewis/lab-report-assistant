"""Optional snapshot transport. Never share a live SQLite database through a drive."""
import base64
from functools import wraps
import json
import os
from pathlib import Path
import re
import ssl
import threading
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler

import local_backup
from app_paths import version

GRAPH = 'https://graph.microsoft.com/v1.0'
AUTH = 'https://login.microsoftonline.com/common/oauth2/v2.0/'
SCOPE = 'Files.ReadWrite.AppFolder offline_access'
NAME = re.compile(r'Labwise-\d{8}T\d{6}Z-[a-f0-9]{8}-[a-f0-9]{8}-[a-f0-9]{12}\.zip\Z')
LOCK = threading.RLock()
OPERATION = threading.Lock()
SESSIONS = {}
DUE = {}


def exclusive(function):
    """Freeze target and account changes throughout a transfer, without waiting."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not OPERATION.acquire(blocking=False):
            raise ValueError('另一个网盘操作正在进行，请稍后重试。')
        try:
            return function(*args, **kwargs)
        finally:
            OPERATION.release()
    return wrapped


def data():
    import pilot_backend
    return pilot_backend.DATA


def session():
    return SESSIONS.setdefault(str(data().resolve()), {})


def config():
    path = data() / 'cloud-backup.json'
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            if not all(re.fullmatch(r'[a-f0-9]{8}', value[k]) for k in ('workspace', 'device')):
                raise ValueError()
            if set(value['targets']) != {'icloud', 'onedrive_folder', 'onedrive'}:
                raise ValueError()
            for target in value['targets'].values():
                if not isinstance(target['folder'], str) or type(target['interval']) is not int or target['interval'] not in (0, 15, 60):
                    raise ValueError()
            return value
        except (ValueError, KeyError, TypeError, UnicodeError):
            raise ValueError('网盘配置无法读取，请保留资料目录并联系维护者。') from None
    return {'workspace': uuid.uuid4().hex[:8], 'device': uuid.uuid4().hex[:8],
            'targets': {p: {'folder': '', 'interval': 0} for p in ('icloud', 'onedrive_folder', 'onedrive')}}


def write_config(value):
    path = data() / 'cloud-backup.json'
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def provider(value):
    if value not in ('icloud', 'onedrive_folder', 'onedrive'):
        raise ValueError('请选择有效的备份目标。')
    return value


def folder(value):
    if not isinstance(value, str) or not value.strip() or not Path(value).expanduser().is_absolute():
        raise ValueError('请选择已存在的网盘文件夹（绝对路径）。')
    root = Path(value).expanduser().resolve()
    active = data().resolve()
    destination = root / 'Labwise Backups'
    if not root.is_dir() or destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError('网盘目录不存在或备份子目录是符号链接。')
    if root == active or root.is_relative_to(active) or active.is_relative_to(destination):
        raise ValueError('网盘备份目录不能与当前资料目录重叠。')
    return destination


def status():
    with LOCK:
        cfg = config()
        # Persist stable identities before any backup is named.
        if not (data() / 'cloud-backup.json').exists():
            write_config(cfg)
        targets = {key: dict(value) for key, value in cfg['targets'].items()}
        targets['onedrive']['connected'] = bool(session().get('tokens'))
        targets['onedrive']['available'] = bool(client_id())
        suggested = Path.home() / 'Library/Mobile Documents/com~apple~CloudDocs'
        for key in ('icloud', 'onedrive_folder'):
            # A label is not proof a user-selected folder belongs to a provider.
            selected = targets[key]['folder']
            targets[key]['location_kind'] = ('icloud' if key == 'icloud' and selected and
                Path(selected).is_relative_to(suggested) else 'custom')
        return {'targets': targets, 'backup_limit_mb': local_backup.LIMIT // 1024**2,
                'icloud_suggestion': str(suggested),
                'version': version(), 'encrypted': False}


@exclusive
def configure(body):
    p = provider(body.get('provider'))
    interval = body.get('interval', 0)
    if type(interval) is not int or interval not in (0, 15, 60):
        raise ValueError('备份间隔应为关闭、15 分钟或 60 分钟。')
    with LOCK:
        cfg = config()
        target = cfg['targets'][p]
        if p != 'onedrive':
            value = body.get('folder', '')
            if value or interval:
                folder(value)
            target['folder'] = str(Path(value).expanduser().resolve())
            if not value:
                target['folder'] = ''
        elif interval and not session().get('tokens'):
            raise ValueError('请先连接 OneDrive 账号。')
        target['interval'] = interval
        write_config(cfg)
        DUE[(str(data().resolve()), p)] = time.monotonic() + interval * 60
    return status()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, method='GET', body=None, token=None, form=False, binary=False, redirects=0):
    """Bound reads; no automatic redirects with credentials; never surface token bodies."""
    import certifi
    headers = {'User-Agent': 'Labwise/' + version()}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if form:
        body = urlencode(body).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    elif body is not None:
        headers['Content-Type'] = 'application/zip'
    opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())))
    try:
        with opener.open(Request(url, data=body, headers=headers, method=method), timeout=30) as response:
            limit = local_backup.LIMIT if binary else 2 * 1024 * 1024
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('网盘响应超过备份大小限额。')
            if binary:
                return raw
            try:
                return json.loads(raw)
            except (ValueError, UnicodeError):
                raise ValueError('网盘返回了无法读取的结果，请稍后重试。') from None
    except HTTPError as error:
        if binary and error.code in (301, 302, 303, 307, 308):
            location = error.headers.get('Location', '')
            host = (urlparse(location).hostname or '').lower()
            if redirects >= 3 or urlparse(location).scheme != 'https' or not any(host.endswith(s) for s in ('.1drv.com', '.sharepoint.com', '.live.com', '.onedrive.com')):
                raise ValueError('网盘下载地址未通过安全校验。') from None
            # The preauthenticated URL is used WITHOUT a Bearer token.
            return request(location, binary=True, redirects=redirects + 1)
        if form:
            try:
                return json.loads(error.read(64 * 1024))
            except (ValueError, UnicodeError):
                pass
        message = {401: 'OneDrive 授权已失效，请重新连接。', 403: 'OneDrive 权限不足，请检查机构授权政策。',
                   429: 'OneDrive 请求过于频繁，请稍后重试。', 507: 'OneDrive 空间不足，请清理后重试。'}.get(error.code, '网盘请求失败，请稍后重试。')
        raise ValueError(message) from None
    except (URLError, TimeoutError, OSError):
        raise ValueError('无法连接网盘，请检查网络后重试。') from None


def client_id():
    value = os.environ.get('LABWISE_ONEDRIVE_CLIENT_ID', '').strip()
    return value if re.fullmatch(r'[a-fA-F0-9-]{36}', value) else ''


@exclusive
def connect():
    with LOCK:
        if not client_id():
            raise ValueError('此安装尚未配置 OneDrive 账号连接，可先使用 OneDrive 客户端目录。')
        if session().get('tokens'):
            raise ValueError('请先断开当前 OneDrive 账号，再连接其他账号。')
        result = request(AUTH + 'devicecode', 'POST', {'client_id': client_id(), 'scope': SCOPE}, form=True)
        if not all(result.get(k) for k in ('device_code', 'user_code', 'verification_uri', 'expires_in')):
            raise ValueError('未能开始微软授权，请检查应用注册配置。')
        uri = result['verification_uri']
        if urlparse(uri).scheme != 'https' or urlparse(uri).hostname not in ('microsoft.com', 'www.microsoft.com', 'login.microsoftonline.com'):
            raise ValueError('微软授权地址未通过校验。')
        session()['pending'] = {**result, 'expires': time.monotonic() + int(result['expires_in']),
                                'next': time.monotonic() + max(5, int(result.get('interval', 5)))}
        return {'user_code': result['user_code'], 'verification_uri': uri,
                'expires_in': result['expires_in'], 'interval': max(5, int(result.get('interval', 5)))}


def save_tokens(result):
    if not result.get('access_token'):
        raise ValueError('OneDrive 授权未完成，请重新连接。')
    session()['tokens'] = {**result, 'expires': time.monotonic() + int(result.get('expires_in', 3600))}
    session().pop('pending', None)


@exclusive
def poll():
    with LOCK:
        pending = session().get('pending')
        if not pending:
            return {'state': 'connected' if session().get('tokens') else 'disconnected'}
        if time.monotonic() >= pending['expires']:
            session().pop('pending', None)
            raise ValueError('微软授权码已过期，请重新连接。')
        if time.monotonic() < pending['next']:
            return {'state': 'pending'}
        result = request(AUTH + 'token', 'POST', {'client_id': client_id(),
                         'grant_type': 'urn:ietf:params:oauth:grant-type:device_code', 'device_code': pending['device_code']}, form=True)
        error = result.get('error')
        if error in ('authorization_pending', 'slow_down'):
            pending['interval'] = max(5, int(pending.get('interval', 5))) + (5 if error == 'slow_down' else 0)
            pending['next'] = time.monotonic() + pending['interval']
            return {'state': 'pending'}
        if error:
            session().pop('pending', None)
            raise ValueError('微软授权被取消、拒绝或已过期，请重新连接。')
        save_tokens(result)
        return {'state': 'connected'}


def access_token():
    with LOCK:
        tokens = session().get('tokens')
        if not tokens:
            raise ValueError('请先连接 OneDrive 账号。')
        if tokens['expires'] <= time.monotonic() + 60:
            if not tokens.get('refresh_token'):
                session().pop('tokens', None)
                raise ValueError('OneDrive 授权已失效，请重新连接。')
            result = request(AUTH + 'token', 'POST', {'client_id': client_id(), 'grant_type': 'refresh_token',
                             'refresh_token': tokens['refresh_token'], 'scope': SCOPE}, form=True)
            if result.get('error'):
                session().pop('tokens', None)
                raise ValueError('OneDrive 授权已失效，请重新连接。')
            result.setdefault('refresh_token', tokens['refresh_token'])
            save_tokens(result)
        return session()['tokens']['access_token']


def graph(path, method='GET', body=None, binary=False):
    return request(GRAPH + path, method, body, token=access_token(), binary=binary)


def remote_items():
    url = '/me/drive/special/approot/children?$top=200'
    items = []
    for _ in range(50):
        response = graph(url)
        for item in response.get('value', []):
            if NAME.fullmatch(item.get('name', '')) and 'file' in item:
                items.append({'id': item['id'], 'name': item['name'], 'size': item.get('size', 0),
                              'modified': item.get('lastModifiedDateTime', '')})
        next_url = response.get('@odata.nextLink')
        if not next_url:
            return sorted(items, key=lambda x: x['name'], reverse=True)
        if not next_url.startswith(GRAPH + '/'):
            raise ValueError('OneDrive 分页地址未通过校验。')
        url = next_url[len(GRAPH):]
    raise ValueError('备份历史过多，请在网盘中整理后重试。')


def _history(p):
    provider(p)
    with LOCK:
        target = config()['targets'][p]
        directory = folder(target['folder']) if p != 'onedrive' else None
    if p == 'onedrive':
        return remote_items()
    if not directory.exists():
        return []
    items = []
    for path in directory.iterdir():
        if NAME.fullmatch(path.name) and not path.is_symlink() and path.is_file():
            items.append({'id': path.name, 'name': path.name, 'size': path.stat().st_size})
    return sorted(items, key=lambda x: x['name'], reverse=True)


history = exclusive(_history)


def record(p, **values):
    with LOCK:
        cfg = config()
        cfg['targets'][p].update(values)
        write_config(cfg)


def backup(p):
    provider(p)
    if not OPERATION.acquire(blocking=False):
        raise ValueError('另一个网盘操作正在进行，请稍后重试。')
    try:
        with LOCK:
            cfg = config()
            write_config(cfg)
            directory = folder(cfg['targets'][p]['folder']) if p != 'onedrive' else None
        import pilot_backend
        timestamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        name = f"Labwise-{timestamp}-{cfg['workspace']}-{cfg['device']}-{uuid.uuid4().hex[:12]}.zip"
        pack = local_backup.create()
        raw = base64.b64decode(pack['content'])
        if p == 'onedrive':
            result = graph('/me/drive/special/approot:/' + quote(name) + ':/content', 'PUT', raw)
            if result.get('size') != len(raw) or result.get('name') != name:
                raise ValueError('OneDrive 上传结果未通过校验，请查看历史后重试。')
            state = 'uploaded'
        else:
            directory.mkdir(exist_ok=True)
            temp = directory / ('.' + name + '.partial')
            try:
                with temp.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                temp.replace(directory / name)
            finally:
                temp.unlink(missing_ok=True)
            state = 'local_written'
        record(p, last_success=pilot_backend.now(), last_attempt=pilot_backend.now(), last_name=name, last_state=state, error='')
        return {'state': state, 'name': name, 'size': len(raw)}
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else '备份未完成，请检查网盘目录权限、空间与网络后重试。'
        import pilot_backend
        record(p, last_attempt=pilot_backend.now(), error=message)
        raise ValueError(message) from None
    finally:
        OPERATION.release()


def restore(p, item_id):
    provider(p)
    if not OPERATION.acquire(blocking=False):
        raise ValueError('另一个网盘操作正在进行，请稍后重试。')
    try:
        item = next((i for i in _history(p) if i['id'] == item_id), None)
        if not item or item['size'] > local_backup.LIMIT:
            raise ValueError('备份不存在或超过 64 MB 限额。')
        if p == 'onedrive':
            raw = graph('/me/drive/items/' + quote(item_id, safe='') + '/content', binary=True)
        else:
            with LOCK:
                path = folder(config()['targets'][p]['folder']) / item['name']
            # A sync client may replace an entry between listing and opening.
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd, 'rb') as stream:
                raw = stream.read(local_backup.LIMIT + 1)
        if len(raw) > local_backup.LIMIT:
            raise ValueError('备份超过 64 MB 限额。')
        return local_backup.restore(base64.b64encode(raw).decode())
    finally:
        OPERATION.release()


@exclusive
def disconnect():
    with LOCK:
        session().clear()
        cfg = config()
        cfg['targets']['onedrive']['interval'] = 0
        write_config(cfg)
    return status()


def dispatch(method, path, body):
    action = path.removeprefix('/api/pilot/cloud/')
    if method == 'GET' and action == 'status':
        return status()
    if method != 'POST':
        raise LookupError('未找到网盘操作。')
    if action == 'configure':
        return configure(body)
    if action == 'connect':
        return connect()
    if action == 'poll':
        return poll()
    if action == 'disconnect':
        return disconnect()
    p = provider(body.get('provider'))
    if action == 'history':
        return {'items': history(p)}
    if action == 'backup':
        return backup(p)
    if action == 'restore':
        return restore(p, body.get('id'))
    raise LookupError('未找到网盘操作。')


def tick():
    with LOCK:
        cfg = config()
        targets = [(p, t['interval']) for p, t in cfg['targets'].items() if t['interval']]
    for p, interval in targets:
        key = (str(data().resolve()), p)
        now = time.monotonic()
        with LOCK:
            due = DUE.setdefault(key, now + interval * 60)
            if now < due:
                continue
            DUE[key] = now + interval * 60
        try:
            backup(p)
        except (ValueError, OSError):
            pass  # backup records a user-visible failure; retry next interval.


def start():
    stop = threading.Event()
    def run():
        while not stop.wait(10):
            try:
                tick()
            except Exception:
                # A damaged local configuration must not stop the local app.
                import logging
                logging.getLogger('labwise.cloud').warning('Cloud backup scheduler unavailable.')
    worker = threading.Thread(target=run, name='labwise-cloud-backup', daemon=True)
    worker.start()
    stop.worker = worker
    return stop
