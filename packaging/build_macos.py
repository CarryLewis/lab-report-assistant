"""Produce a self-contained local trial app and a drag-to-install disk image."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import plistlib
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_paths import release_channel, stable_version, version as app_version

beta_build = release_channel() == 'beta'
BUILD = Path(os.environ.get('LABWISE_BUILD_DIR', str(ROOT / 'output' / (f'build-beta-{app_version()}' if beta_build else 'build')))).expanduser().resolve()
RELEASE = Path(os.environ.get('LABWISE_RELEASE_DIR', str(ROOT / 'output' / (f'beta-{app_version()}' if beta_build else 'installers')))).expanduser().resolve()


def bundle_libreoffice(app):
    source = Path(os.environ.get('LABWISE_LIBREOFFICE_APP', '/Applications/LibreOffice.app')).expanduser().resolve()
    executable = source / 'Contents/MacOS/soffice'
    if not executable.is_file():
        raise SystemExit('构建需要完整 LibreOffice.app；请通过 LABWISE_LIBREOFFICE_APP 指定原版组件目录。')
    architectures = subprocess.check_output(['lipo', '-archs', str(executable)], text=True).split()
    if platform.machine() not in architectures:
        raise SystemExit('LibreOffice 架构与 Labwise 安装包不一致。')
    info = plistlib.loads((source / 'Contents/Info.plist').read_bytes())
    target = app / 'Contents/Helpers/LibreOffice.app'
    target.parent.mkdir(parents=True, exist_ok=True)
    run('ditto', source, target)
    # Finder icon metadata from the disk image is not part of executable content
    # and prevents sealing the enclosing app. Leave all security attributes alone.
    paths = [str(app)] + [str(p) for p in app.rglob('*') if not p.is_symlink()]
    for offset in range(0, len(paths), 100):
        for attribute in ('com.apple.FinderInfo', 'com.apple.ResourceFork'):
            subprocess.run(['/usr/bin/xattr', '-d', attribute, *paths[offset:offset + 100]],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    license_folder = app / 'Contents/Resources/third-party-licenses/LibreOffice'
    license_folder.mkdir(parents=True, exist_ok=True)
    for name in ('LICENSE', 'LICENSE.html', 'NOTICE'):
        shutil.copy2(source / 'Contents/Resources' / name, license_folder / name)
    version = info['CFBundleShortVersionString']
    (license_folder / 'SOURCE.txt').write_text(
        f'LibreOffice {version}, The Document Foundation and contributors.\n'
        'Bundled as a separate conversion application; source code is not modified.\n'
        'Local trial build signatures are applied to the bundled executables.\n'
        'License terms and third-party notices are in LICENSE and NOTICE.\n'
        'Source code and release archives: https://download.documentfoundation.org/libreoffice/src/\n'
        'Archived releases: https://downloadarchive.documentfoundation.org/libreoffice/old/\n'
        f'Corresponding core source tag: libreoffice-{version}\n'
        'Source repository: https://git.libreoffice.org/core\n'
        'Licenses: https://www.libreoffice.org/licenses/\n')
    # Sign our local trial copy, including its nested plug-ins and libraries.
    # The separate system installation is never modified.
    run('codesign', '--force', '--deep', '--sign', '-', target)
    run('codesign', '--verify', '--deep', '--strict', target)
    # File-provider managed folders can recreate the enclosing app's Finder
    # icon metadata during a long nested signing pass. Clear it at seal time.
    for attribute in ('com.apple.FinderInfo', 'com.apple.ResourceFork'):
        subprocess.run(['/usr/bin/xattr', '-d', attribute, str(app)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run('codesign', '--force', '--sign', '-', app)
    return {'bundled': True, 'version': version, 'architectures': architectures,
            'relative_path': 'Contents/Helpers/LibreOffice.app',
            'source_executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest()}


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
    channel = release_channel()
    beta = channel == 'beta'
    app_name = 'Labwise Beta.app' if beta else 'Labwise.app'
    architecture = platform.machine()
    assets = BUILD / 'package-assets'
    if assets.exists():
        shutil.rmtree(assets)
    assets.mkdir(parents=True)
    notices(assets / 'third-party-licenses')
    info = {'application':'Labwise','version':version,'architecture':architecture,
            'release_channel':channel,'stable_version':stable_version(), 'application_bundle':app_name,
            'tested_build_os':platform.mac_ver()[0], 'distribution':'local-trial',
            'developer_id_signed':False,'notarized':False,
            'source_hashes':{file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(ROOT.glob('*.py'))}}
    (assets/'build-info.json').write_text(json.dumps(info,indent=2))
    environment = dict(__import__('os').environ)
    environment['PYINSTALLER_CONFIG_DIR'] = str(BUILD/'pyinstaller-cache')
    environment['LABWISE_PACKAGE_ASSETS'] = str(assets)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean',
                    '--distpath',str(BUILD/'macos-dist'),'--workpath',str(BUILD/'macos-work'),
                    str(ROOT/'packaging'/'macos.spec')],cwd=ROOT,env=environment,check=True)
    app = BUILD/'macos-dist'/app_name
    info['libreoffice'] = bundle_libreoffice(app)
    run('codesign','--verify','--deep','--strict',app)
    preflight = BUILD/'packaged-preflight.json'
    run(app/'Contents/MacOS/Labwise','--self-test','--gui-self-test','--report',preflight)
    status = json.loads(preflight.read_text())
    if not status['runtime_ok'] or status['missing_resources'] or not status.get('data_outside_program'):
        raise SystemExit('打包后的运行检查失败，未生成安装交付物。')
    if status.get('version') != version or status.get('release_channel') != channel or status.get('stable_version') != stable_version():
        raise SystemExit('包内版本或发布渠道标识不一致，停止生成安装包。')
    if beta and Path(status['default_data_directory']).parent.name != 'Labwise Beta':
        raise SystemExit('测试版默认资料目录未独立，停止生成安装包。')
    expected_converter = app / 'Contents/Helpers/LibreOffice.app/Contents/MacOS/soffice'
    if status.get('word_converter') != str(expected_converter) or not status['paged_word_export']:
        raise SystemExit('未启用包内 Word 转换组件，停止生成安装包。')
    forbidden = {'.labwise','deepseek_api_key','.env','pilot.sqlite3','historical'}
    if any(path.name in forbidden or path.suffix in ('.sqlite3','.docx') for path in app.rglob('*')
           if not path.is_relative_to(app / 'Contents/Helpers/LibreOffice.app')):
        raise SystemExit('交付物含不允许分发的资料文件，已停止。')
    conversion_report = BUILD / f'bundled-converter-smoke-{version}.json'
    run(sys.executable, ROOT/'packaging/smoke_bundled_converter.py', app, '--report', conversion_report)
    info['bundled_converter_verification'] = json.loads(conversion_report.read_text())
    # Keep verification records alongside the distributable, even when a local
    # file-provider folder requires building in a separate temporary directory.
    audit = ROOT / 'output/build'
    audit.mkdir(parents=True, exist_ok=True)
    if BUILD != audit:
        shutil.copy2(conversion_report, audit / conversion_report.name)
        shutil.copy2(preflight, audit / preflight.name)
    stage = BUILD/'dmg-stage'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    run('ditto',app,stage/app_name)
    (stage/'Applications').symlink_to('/Applications')
    shutil.copy2(ROOT/'packaging'/'INSTALL.zh.txt',stage/'安装与使用说明.txt')
    RELEASE.mkdir(parents=True,exist_ok=True)
    stem = f'Labwise-{version}{"-beta" if beta else ""}-macOS-{architecture}-trial'
    dmg = RELEASE/(stem+'.dmg')
    run('hdiutil','create','-volname','Labwise '+version+(' 测试版' if beta else ' 本机试用'),'-srcfolder',stage,'-format','UDZO','-ov',dmg)
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
