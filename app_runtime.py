"""Desktop lifecycle, preflight checks and single-instance loopback service."""
import argparse
import errno
import importlib
import json
import logging
import os
from pathlib import Path
import queue
import sys
import threading
from urllib.request import ProxyHandler, build_opener
import uuid
import webbrowser

from app_paths import ROOT, data_directory, version

REQUIRED_MODULES = ('certifi', 'pypdf', 'pdfplumber', 'PIL.Image', 'pypdfium2', 'reportlab', 'tkinter')
REQUIRED_FILES = ('review-layout.css','design-system.css', 'i18n.js', 'i18n-en.js', 'i18n-init.js', 'i18n.css', 'index.html', 'teacher-live.js', 'teacher-live.css', 'user-support.js',
                  'user-support.css', 'word-reader.html', 'word-reader.js',
                  'pdf-export.js', 'pdf-export.css', 'vendor/pdfjs/pdf.mjs', 'corpus/writing_profiles.json', 'VERSION')


def preflight():
    modules = {}
    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
            modules[name] = True
        except Exception:
            modules[name] = False
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    try:
        import certifi
        import ssl
        context = ssl.create_default_context(cafile=certifi.where())
        tls_ready = context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    except Exception:
        tls_ready = False
    from document_preview import converter_path
    converter = converter_path()
    return {'application': 'Labwise', 'version': version(), 'architecture': os.uname().machine if hasattr(os, 'uname') else 'unknown',
            'runtime_ok': all(modules.values()) and tls_ready, 'tls_ready':tls_ready, 'modules': modules, 'missing_resources': missing,
            'data_outside_program': not data_directory().resolve().is_relative_to(ROOT.resolve()),
            'paged_word_export': bool(converter),
            'word_converter': converter,
            'warnings': [] if converter else ['未找到 Word 分页转换组件。原文阅读、评分和 Word 批改包可用；评阅 PDF 需要安装 LibreOffice 后重新检查。']}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def probe_instance(record):
    try:
        port = record['port']
        if type(port) is not int or not 1 <= port <= 65535:
            return False
        # Local readiness must never go through a configured Internet proxy.
        with build_opener(ProxyHandler({})).open(f'http://127.0.0.1:{port}/api/pilot/health', timeout=2) as response:
            status = json.loads(response.read(8192))
        return status.get('application') == 'Labwise' and status.get('instance_id') == record.get('instance_id')
    except Exception:
        return False


class DesktopService:
    def __init__(self, directory=None, port=8001):
        self.directory = Path(directory or data_directory()).resolve()
        self.port = port
        self.server = None
        self.thread = None
        self.lock = None
        self.record = None
        self.reused = False

    def start(self):
        if not 0 <= self.port <= 65535:
            raise ValueError('端口应为 0–65535。')
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        import fcntl
        self.lock = (self.directory / '.desktop.lock').open('a+')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            self.lock = None
            try:
                existing = json.loads((self.directory / 'app-instance.json').read_text())
            except (OSError, ValueError):
                existing = {}
            if probe_instance(existing):
                self.reused = True
                self.record = existing
                return existing
            raise RuntimeError('同一资料目录的应用正在启动或尚未退出，请稍候重试；不会另开第二个资料服务。')
        try:
            import pilot_backend
            import server
            pilot_backend.DATA = self.directory
            ports = [0] if self.port == 0 else [*range(self.port, min(self.port + 10, 65536)), 0]
            for candidate in ports:
                try:
                    self.server = server.create_server('127.0.0.1', candidate)
                    break
                except OSError as error:
                    if error.errno != errno.EADDRINUSE:
                        raise
            if self.server is None:
                raise RuntimeError('没有可用的本机端口，请关闭其他试用实例后重试。')
            actual = self.server.server_address[1]
            self.record = {'application':'Labwise', 'port':actual, 'url':f'http://127.0.0.1:{actual}/',
                           'instance_id':self.server.instance_id, 'version':version()}
            self.thread = threading.Thread(target=self.server.serve_forever, name='labwise-http', daemon=True)
            self.thread.start()
            write_json(self.directory / 'app-instance.json', self.record)
            return self.record
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.server:
            if self.thread and self.thread.is_alive():
                self.server.shutdown()
                self.thread.join(timeout=5)
            self.server.server_close()
            self.server = None
        if self.lock:
            try:
                record = self.directory / 'app-instance.json'
                if self.record and json.loads(record.read_text()).get('instance_id') == self.record['instance_id']:
                    record.unlink()
            except (OSError, ValueError):
                pass
            self.lock.close()
            self.lock = None


def run_headless(args):
    service = DesktopService(args.data_dir, args.port)
    try:
        record = service.start()
        if args.ready_file:
            write_json(args.ready_file, record)
        if service.reused:
            return 0
        if args.open_browser:
            webbrowser.open(record['url'])
        service.thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
    return 0


def run_desktop(args):
    import tkinter as tk
    from tkinter import messagebox, ttk
    root = tk.Tk()
    root.title('Labwise '+version()+' · 本机试用版')
    root.geometry('660x380')
    root.minsize(600, 340)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Labwise 教师工作区', font=('', 21, 'bold')).pack(anchor='w')
    status = tk.StringVar(value='正在检查运行环境并启动…')
    ttk.Label(frame, textvariable=status, wraplength=600).pack(anchor='w', pady=(16, 8))
    location = Path(args.data_dir or data_directory()).resolve()
    ttk.Label(frame, text='资料独立保存在：\n' + str(location), wraplength=600).pack(anchor='w', pady=(0, 12))
    notes = tk.StringVar(value='本机试用构建 · 不会自动发布学生成绩。')
    ttk.Label(frame, textvariable=notes, wraplength=600).pack(anchor='w', pady=(0, 12))
    service = DesktopService(location, args.port)
    events = queue.Queue()
    opened = False
    launch = ttk.Button(frame, text='打开教师工作台', state='disabled', command=lambda:webbrowser.open(service.record['url']))
    launch.pack(anchor='w', pady=6)
    def open_folder():
        import subprocess
        subprocess.Popen(['open', str(location)])
    ttk.Button(frame, text='打开资料目录', command=open_folder).pack(anchor='w', pady=6)
    def close():
        if opened and not service.reused and not messagebox.askokcancel('退出 Labwise', '请先在工作台保存草稿。退出会中断尚未完成的分析，重新打开后可重试。\n\n现在退出？', parent=root):
            return
        root.destroy()
    quit_button = ttk.Button(frame, text='退出应用', command=close)
    quit_button.pack(anchor='w', pady=6)
    root.protocol('WM_DELETE_WINDOW', close)
    def start():
        try:
            report = preflight()
            if not report['runtime_ok'] or report['missing_resources']:
                raise RuntimeError('应用运行依赖或界面文件不完整，请重新解压完整安装包；源码运行请按安装说明准备依赖。')
            record = service.start()
            events.put(('ready', record, report))
        except Exception as error:
            logging.exception('Desktop startup failed')
            events.put(('error', str(error), None))
    def poll():
        nonlocal opened
        try:
            kind, value, report = events.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        if kind == 'error':
            status.set('启动未完成：' + value)
            return
        status.set(('已有工作区正在运行，已复用。' if service.reused else '工作区已就绪。') + '\n' + value['url'])
        notes.set('\n'.join(report['warnings']) or '运行环境检查通过。请在工作台配置分析服务。')
        launch.configure(state='normal')
        if service.reused:
            quit_button.configure(text='关闭此窗口（现有工作区继续运行）')
        opened = True
        if args.open_browser:
            webbrowser.open(value['url'])
    threading.Thread(target=start, name='labwise-startup', daemon=True).start()
    root.after(100, poll)
    try:
        root.mainloop()
    finally:
        service.stop()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Labwise 本机工作区')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--port', type=int, default=int(os.environ.get('LABWISE_PORT', '8001')))
    parser.add_argument('--serve', action='store_true', help='运行本机服务，不显示启动窗口')
    parser.add_argument('--self-test', action='store_true', help='检查打包资源和依赖，不启动服务')
    parser.add_argument('--gui-self-test', action='store_true', help='自检时初始化并关闭隐藏启动窗口')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--ready-file', type=Path)
    parser.add_argument('--no-browser', dest='open_browser', action='store_false', default=True)
    args = parser.parse_args(argv)
    if args.self_test:
        report = preflight()
        if args.gui_self_test:
            try:
                import tkinter as tk
                window = tk.Tk()
                window.withdraw()
                window.update()
                window.destroy()
                report['gui_ready'] = True
            except Exception as error:
                report.update(gui_ready=False, runtime_ok=False, gui_error=type(error).__name__)
        if args.report:
            write_json(args.report, report)
        elif sys.stdout:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['runtime_ok'] and not report['missing_resources'] else 1
    directory = Path(args.data_dir or data_directory()).resolve()
    from logging.handlers import RotatingFileHandler
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        handlers = [RotatingFileHandler(directory / 'startup.log', maxBytes=1_000_000, backupCount=2, encoding='utf-8')]
    except OSError:
        handlers = [logging.NullHandler()]
    logging.basicConfig(handlers=handlers, level=logging.WARNING)
    return run_headless(args) if args.serve else run_desktop(args)
