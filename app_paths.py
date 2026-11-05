"""Read-only program resources and persistent user data have separate homes."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def release_channel():
    path = ROOT / 'RELEASE_CHANNEL'
    return path.read_text().strip() if path.is_file() else 'stable'


def stable_version():
    path = ROOT / 'STABLE_VERSION'
    return path.read_text().strip() if path.is_file() else version()


def data_directory():
    explicit = os.environ.get('LABWISE_DATA_DIR', '').strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    if getattr(sys, 'frozen', False):
        application = 'Labwise Beta' if release_channel() == 'beta' else 'Labwise'
        if sys.platform == 'darwin':
            return Path.home() / 'Library' / 'Application Support' / application / 'data'
        if sys.platform == 'win32':
            return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / application / 'data'
        return Path.home() / '.local' / 'share' / ('labwise-beta' if release_channel() == 'beta' else 'labwise') / 'data'
    # Existing source checkouts retain their data; never silently move a course.
    return ROOT / '.labwise'


def version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
