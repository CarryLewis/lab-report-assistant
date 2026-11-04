"""Build only program resources; teacher files are never in this manifest."""
from pathlib import Path
import ast
import json
import os
import platform
import ssl
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
tree = ast.parse((root / 'server.py').read_text())
public = set()
for assignment in ast.walk(tree):
    if isinstance(assignment, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'public' for target in assignment.targets):
        public = ast.literal_eval(assignment.value)
assets = {path.lstrip('/') for path in public if path != '/'} | {'VERSION'}
datas = [(str(root / name), str(Path(name).parent)) for name in sorted(assets)]
datas += [(str(root / 'corpus' / 'writing_profiles.json'), 'corpus'),
          (str(root / 'vendor'), 'vendor'),
          (os.environ.get('LABWISE_PACKAGE_ASSETS', str(root / 'output/build/package-assets')), 'release-info')]
# This host's managed Python patches ssl to load this public certificate policy
# resource beside ssl.py. Preserve that policy instead of disabling TLS checks.
certificate_policy = Path(ssl.__file__).with_name('codex-rejected-cas.pem')
if certificate_policy.is_file():
    datas.append((str(certificate_policy), '.'))
binaries, hidden = [], []
for package in ('certifi', 'pypdfium2', 'pypdfium2_raw', 'reportlab'):
    package_data, package_bins, package_hidden = collect_all(package)
    datas += package_data
    binaries += package_bins
    hidden += package_hidden

a = Analysis([str(root / 'launcher.py')], pathex=[str(root)], binaries=binaries, datas=datas,
             hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'IPython', 'pytest', 'unittest', 'pydoc'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Labwise', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          argv_emulation=False, target_arch=platform.machine(), codesign_identity=None,
          entitlements_file=None)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Labwise')
app = BUNDLE(collection, name='Labwise.app', icon=None, bundle_identifier='com.carrylewis.labwise',
             info_plist={'CFBundleShortVersionString':(root/'VERSION').read_text().strip(),
                         'CFBundleVersion':'20261104.1', 'NSHighResolutionCapable':True,
                         'LSMultipleInstancesProhibited':True,
                         'NSHumanReadableCopyright':'Labwise local trial. Third-party notices are included.'})
