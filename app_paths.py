"""Read-only program resources and persistent user data have separate homes."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def data_directory():
    explicit = os.environ.get('LABWISE_DATA_DIR', '').strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            return Path.home() / 'Library' / 'Application Support' / 'Labwise' / 'data'
        if sys.platform == 'win32':
            return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Labwise' / 'data'
        return Path.home() / '.local' / 'share' / 'labwise' / 'data'
    # Existing source checkouts retain their data; never silently move a course.
    return ROOT / '.labwise'


def version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
