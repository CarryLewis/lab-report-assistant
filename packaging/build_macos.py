"""Produce a self-contained local trial app and a drag-to-install disk image."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'output' / 'build'
RELEASE = ROOT / 'output' / 'installers'


def run(*args):
    subprocess.run([str(value) for value in args], check=True)


def notices(target):
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for name in ('certifi','pypdf','pdfplumber','pdfminer.six','Pillow','pypdfium2','reportlab',
                 'cryptography','cffi','charset-normalizer','pycparser','PyInstaller'):
        try:
            dist = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        records.append({'name':dist.metadata['Name'], 'version':dist.version,
                        'license':dist.metadata.get('License-Expression') or dist.metadata.get('License','See included license files')})
        for file in dist.files or []:
            if any(part.lower() in ('licenses', 'license', 'copying') for part in file.parts) or any(word in file.name.lower() for word in ('license','copying','notice')):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    destination = target / name / str(file)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    (target / 'components.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    python_license = Path(sys.base_prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'LICENSE.txt'
    if python_license.is_file():
        shutil.copy2(python_license, target / 'Python-LICENSE.txt')


def main():
    if sys.platform != 'darwin':
        raise SystemExit('macOS 应用需要在 macOS 上构建。')
    version = (ROOT/'VERSION').read_text().strip()
    architecture = platform.machine()
    assets = BUILD / 'package-assets'
    if assets.exists():
        shutil.rmtree(assets)
    assets.mkdir(parents=True)
    notices(assets / 'third-party-licenses')
    info = {'application':'Labwise','version':version,'architecture':architecture,
            'tested_build_os':platform.mac_ver()[0], 'distribution':'local-trial',
            'developer_id_signed':False,'notarized':False,
            'source_hashes':{file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(ROOT.glob('*.py'))}}
    (assets/'build-info.json').write_text(json.dumps(info,indent=2))
    environment = dict(__import__('os').environ)
    environment['PYINSTALLER_CONFIG_DIR'] = str(BUILD/'pyinstaller-cache')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean',
                    '--distpath',str(BUILD/'macos-dist'),'--workpath',str(BUILD/'macos-work'),
                    str(ROOT/'packaging'/'macos.spec')],cwd=ROOT,env=environment,check=True)
    app = BUILD/'macos-dist'/'Labwise.app'
    run('codesign','--verify','--deep','--strict',app)
    preflight = BUILD/'packaged-preflight.json'
    run(app/'Contents/MacOS/Labwise','--self-test','--gui-self-test','--report',preflight)
    status = json.loads(preflight.read_text())
    if not status['runtime_ok'] or status['missing_resources'] or not status.get('data_outside_program'):
        raise SystemExit('打包后的运行检查失败，未生成安装交付物。')
    forbidden = {'.labwise','deepseek_api_key','.env','pilot.sqlite3','historical'}
    if any(path.name in forbidden or path.suffix in ('.sqlite3','.docx') for path in app.rglob('*')):
        raise SystemExit('交付物含不允许分发的资料文件，已停止。')
    stage = BUILD/'dmg-stage'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    run('ditto',app,stage/'Labwise.app')
    (stage/'Applications').symlink_to('/Applications')
    shutil.copy2(ROOT/'packaging'/'INSTALL.zh.txt',stage/'安装与使用说明.txt')
    RELEASE.mkdir(parents=True,exist_ok=True)
    stem = f'Labwise-{version}-macOS-{architecture}-trial'
    dmg = RELEASE/(stem+'.dmg')
    run('hdiutil','create','-volname','Labwise 本机试用','-srcfolder',stage,'-format','UDZO','-ov',dmg)
    run('hdiutil','verify',dmg)
    archive = RELEASE/(stem+'.zip')
    run('ditto','-c','-k','--sequesterRsrc','--keepParent',app,archive)
    release_info = {**info,'preflight':status,
                    'files':{file.name:{'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size} for file in (dmg,archive)}}
    (RELEASE/(stem+'-manifest.json')).write_text(json.dumps(release_info,ensure_ascii=False,indent=2))
    shutil.copy2(ROOT/'packaging'/'INSTALL.zh.txt',RELEASE/'安装与使用说明.txt')
    print('已生成：'+str(dmg))
    print('已生成：'+str(archive))


if __name__ == '__main__':
    main()
