#!/usr/bin/env python3
"""Build an offline, relocated ARM64 Termux prefix from signed upstream packages."""
import concurrent.futures
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

from prepare_project import REPO, WORK, PROJECT, LOCK

CACHE = WORK / 'downloads'
BASE = 'https://packages.termux.dev/apt/termux-main/'
TERMUX_APK = 'https://github.com/termux/termux-app/releases/download/v0.118.3/termux-app_v0.118.3%2Bgithub-debug_arm64-v8a.apk'
X11_APK = 'https://github.com/termux/termux-x11/releases/download/nightly/termux-x11-universal-debug.apk'
PAIRS = [('data/data/com.termux', 'data/data/com.archoh'),
         ('data/user/0/com.termux', 'data/user/0/com.archoh'),
         ('"com.termux"', '"com.archoh"'), ("'com.termux'", "'com.archoh'"),
         ('com.termux/com.termux.', 'com.archoh/com.termux.'),
         ('com.termux.service_', 'com.archoh.service_'),
         ('com.termux.app.reload_style', 'com.archoh.app.reload_style'),
         ('com.termux.app.request_storage_permissions', 'com.archoh.app.request_storage_permissions')]

def relocate(data):
    for old, new in PAIRS:
        assert len(old) == len(new)
        data = data.replace(old.encode(), new.encode())
    return data

def download(url, name, sha=None):
    path = CACHE / name
    if not path.exists():
        temp = path.with_suffix(path.suffix + '.partial')
        subprocess.run(['curl', '-fL', '--proto', '=https', '--proto-redir', '=https', '--retry', '4', '--connect-timeout', '30', '--max-time', '600', url, '-o', str(temp)], check=True)
        temp.rename(path)
    if sha and hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        path.unlink()
        raise RuntimeError(f'Checksum mismatch: {name}')
    return path

def paragraphs(text):
    result = []
    for paragraph in text.strip().split('\n\n'):
        fields = {}
        key = None
        for line in paragraph.splitlines():
            if line.startswith((' ', '\t')) and key:
                fields[key] += '\n' + line
            elif ': ' in line:
                key, value = line.split(': ', 1)
                fields[key] = value
        if fields:
            result.append(fields)
    return result

def ar_members(data):
    if not data.startswith(b'!<arch>\n'):
        raise ValueError('Not a Debian ar archive')
    offset = 8
    while offset < len(data):
        header = data[offset:offset+60]
        if len(header) != 60 or header[58:60] != b'`\n':
            raise ValueError('Invalid ar header')
        size = int(header[48:58])
        name = header[:16].decode().strip().rstrip('/')
        yield name, data[offset+60:offset+60+size]
        offset += 60 + size + (size % 2)

def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    sums = download('https://github.com/termux/termux-app/releases/download/v0.118.3/termux-app_v0.118.3%2Bgithub-debug_sha256sums', 'termux-sha256sums')
    expected = next(line.split()[0] for line in sums.read_text().splitlines() if line.endswith('github-debug_arm64-v8a.apk'))
    termux_apk = download(TERMUX_APK, 'termux.apk', expected)
    x11_apk = download(X11_APK, 'x11.apk', LOCK['x11_apk_sha256'])
    with zipfile.ZipFile(termux_apk) as apk:
        bootstrap = zipfile.ZipFile(io.BytesIO(apk.read('lib/arm64-v8a/libtermux-bootstrap.so')))
        termux_jni = apk.read('lib/arm64-v8a/libtermux.so')
    records = paragraphs(bootstrap.read('var/lib/dpkg/status').decode())
    # Authenticate APT metadata using public keyrings from the verified bootstrap.
    keyring = WORK / 'termux-upstream.gpg'
    keyring.write_bytes(b''.join(bootstrap.read(n) for n in bootstrap.namelist() if n.startswith('share/termux-keyring/') and n.endswith('.gpg')))
    entries = []
    for label, base, suite in [('main',BASE,'stable'),('x11','https://packages.termux.dev/apt/termux-x11/','x11')]:
        inrelease = download(base+'dists/'+suite+'/InRelease', label+'-InRelease')
        release = WORK / (label+'-Release')
        if release.exists(): release.unlink()
        subprocess.run(['gpgv', '--keyring', str(keyring), '--output', str(release), str(inrelease)], check=True)
        signed_hashes = {}
        in_sha256 = False
        for line in release.read_text().splitlines():
            if line == 'SHA256:':
                in_sha256 = True
            elif line and not line.startswith(' '):
                in_sha256 = False
            elif in_sha256 and line.strip():
                digest, size, name = line.split()
                signed_hashes[name] = digest
        index_name = 'main/binary-aarch64/Packages.gz'
        index = download(base+'dists/'+suite+'/'+index_name, label+'-Packages.gz', signed_hashes[index_name])
        for entry in paragraphs(gzip.decompress(index.read_bytes()).decode()):
            entry['_base'] = base
            entries.append(entry)
    packages = {p['Package']: p for p in entries}
    providers = {}
    for p in entries:
        for provided in p.get('Provides', '').split(','):
            name = provided.strip().split(' ')[0]
            if name:
                providers.setdefault(name, p['Package'])
    wanted = set()
    def include(name):
        name = name.split(':')[0]
        if name not in packages:
            name = providers.get(name, name)
        if name in wanted:
            return
        if name not in packages:
            raise RuntimeError(f'Unresolved runtime dependency: {name}')
        wanted.add(name)
        p = packages[name]
        for group in (p.get('Pre-Depends', '') + ',' + p.get('Depends', '')).split(','):
            choices = [re.split(r'[ (]', c.strip())[0].split(':')[0] for c in group.split('|') if c.strip()]
            if not choices:
                continue
            choice = next((c for c in choices if c in packages or c in providers), None)
            if choice is None:
                raise RuntimeError(f'Unresolved dependency of {name}: {group}')
            include(choice)
    # Current util-linux includes lsns but omits libmount from its dependency field.
    for name in sorted({p['Package'] for p in records} | {'proot', 'pulseaudio', 'procps', 'tar', 'xz-utils', 'x11-repo', 'xkeyboard-config', 'xorg-xkbcomp', 'libmount'}):
        include(name)
    def fetch_package(name):
        p = packages[name]
        return name, download(p['_base']+p['Filename'], Path(p['Filename']).name, p['SHA256'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        downloads = dict(pool.map(fetch_package, sorted(wanted)))
    files = {e.filename: (bootstrap.read(e.filename), e.external_attr >> 16) for e in bootstrap.infolist() if not e.is_dir() and e.filename != 'SYMLINKS.txt'}
    links = {}
    for line in bootstrap.read('SYMLINKS.txt').decode().splitlines():
        target, name = line.split('←')
        links[name.removeprefix('./')] = target
    # Remove files owned by the old bootstrap packages BEFORE overlaying any new
    # package, so package splits cannot leave obsolete ELF binaries behind.
    for old in records:
        name=old['Package']
        list_name=f'var/lib/dpkg/info/{name}.list'
        if list_name in bootstrap.namelist():
            for path in bootstrap.read(list_name).decode().splitlines():
                relative=path.removeprefix('/').removeprefix('data/data/com.termux/files/usr/').removeprefix('./')
                files.pop(relative,None)
                links.pop(relative,None)
        for path in list(files):
            if path.startswith(f'var/lib/dpkg/info/{name}.'):
                del files[path]
    status = []
    for name in sorted(wanted):
        members = dict(ar_members(downloads[name].read_bytes()))
        data_member = next(k for k in members if k.startswith('data.tar'))
        control_member = next(k for k in members if k.startswith('control.tar'))
        # zstd is decoded using the official system tool on the build host.
        def unpack(data, suffix):
            if suffix.endswith('.zst'):
                data = subprocess.run(['zstd', '-dc'], input=data, stdout=subprocess.PIPE, check=True).stdout
            return tarfile.open(fileobj=io.BytesIO(data), mode='r:*')
        installed = []
        with unpack(members[data_member], data_member) as data:
            for member in data:
                path = member.name.removeprefix('./')
                prefix = 'data/data/com.termux/files/usr/'
                if not path.startswith(prefix):
                    if path.rstrip('/') in ('', 'data', 'data/data', 'data/data/com.termux', 'data/data/com.termux/files', prefix.rstrip('/')):
                        continue
                    if member.isdir():
                        continue
                    raise RuntimeError(f'Unexpected package path: {path}')
                path = path[len(prefix):]
                if path.startswith('libexec/installed-tests/'):
                    continue
                if '..' in PurePosixPath(path).parts:
                    raise RuntimeError('Unsafe upstream path')
                installed.append('/data/data/com.archoh/files/usr/'+path)
                if member.issym():
                    links[path] = relocate(member.linkname.encode()).decode()
                    files.pop(path, None)
                elif member.isreg():
                    files[path] = (relocate(data.extractfile(member).read()), member.mode)
                    links.pop(path, None)
                elif member.islnk():
                    target = member.linkname.removeprefix('./').removeprefix(prefix)
                    if target not in files:
                        raise RuntimeError(f'Unsupported forward upstream hardlink: {path}')
                    files[path] = files[target]
                    links.pop(path, None)
        with unpack(members[control_member], control_member) as control:
            fields = None
            for member in control:
                if not member.isreg():
                    continue
                control_name = member.name.removeprefix('./')
                body = relocate(control.extractfile(member).read())
                if control_name == 'control':
                    fields = body.decode().strip()
                else:
                    files[f'var/lib/dpkg/info/{name}.{control_name}'] = (body, member.mode)
            if fields is None:
                raise RuntimeError(f'Package has no control record: {name}')
            status.append(fields+'\nStatus: install ok unpacked\n')
        files[f'var/lib/dpkg/info/{name}.list'] = (('\n'.join(installed)+'\n').encode(), 0o644)
    files['var/lib/dpkg/status'] = (('\n'.join(status)+'\n').encode(), 0o644)
    if 'bin/sh' not in files and 'bin/sh' not in links:
        links['bin/sh']='bash'
    for name in list(files):
        if name.startswith('libexec/installed-tests/'):
            del files[name]
    for name in list(links):
        if name.startswith('libexec/installed-tests/'):
            del links[name]
    # Offline payload defaults; device migration applies the same choice after dpkg.
    files['etc/apt/sources.list'] = (b'deb https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main stable main\n', 0o644)
    files['etc/apt/sources.list.d/x11.list'] = (b'deb https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-x11 x11 main\n', 0o644)
    links['etc/termux/chosen_mirrors'] = 'mirrors/chinese_mainland/mirrors.tuna.tsinghua.edu.cn'
    files.pop('etc/termux/chosen_mirrors', None)
    # Public relocation hook keeps subsequent apt operations scoped to this APK.
    hook = '''#!/data/data/com.archoh/files/usr/bin/sh
set -eu
PREFIX=/data/data/com.archoh/files/usr
export CLASSPATH="$(cat "$PREFIX/../apk-path")"
unset LD_LIBRARY_PATH LD_PRELOAD
exec /system/bin/app_process /system/bin --nice-name=archohall-relocate com.termux.app.PackageRelocator --apt
'''
    files['bin/archohall-relocate-packages'] = (hook.encode(), 0o755)
    files['etc/apt/apt.conf.d/99archohall-relocate'] = (b'DPkg::Pre-Install-Pkgs {"/data/data/com.archoh/files/usr/bin/archohall-relocate-packages";};\n', 0o644)
    files['SYMLINKS.txt'] = (''.join(relocate(t.encode()).decode()+'←'+n+'\n' for n,t in sorted(links.items())).encode(), 0o644)
    for name, (data, mode) in list(files.items()):
        files[name] = (relocate(data), mode)
    for name,(body,mode) in list(files.items()):
        if not name.endswith('.md5sums'):
            continue
        refreshed=[]
        for line in body.decode().splitlines():
            if len(line)<34:
                continue
            path=line[34:].removeprefix('data/data/com.archoh/files/usr/')
            if path in files:
                refreshed.append(hashlib.md5(files[path][0]).hexdigest()+line[32:])
        files[name]=(('\n'.join(refreshed)+'\n').encode(),mode)
    assets = PROJECT/'app/src/main/assets'
    assets.mkdir(parents=True, exist_ok=True)
    output = assets/'bootstrap-relocated.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, (body, mode) in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026,1,1,0,0,0))
            info.external_attr = (0o100000 | (mode & 0o777)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, body)
    required = ['bin/proot', 'bin/bash', 'bin/tar', 'bin/xz', 'bin/pulseaudio']
    for name in required:
        if name not in files and name not in links:
            raise RuntimeError(f'Missing bundled executable: {name}')
    jni = PROJECT/'app/src/main/jniLibs/arm64-v8a'
    jni.mkdir(parents=True, exist_ok=True)
    (jni/'libtermux.so').write_bytes(termux_jni)
    with zipfile.ZipFile(x11_apk) as apk:
        native = relocate(apk.read('lib/arm64-v8a/libXlorie.so'))
    x11_jni = PROJECT/'lorie/src/main/jniLibs/arm64-v8a'
    x11_jni.mkdir(parents=True, exist_ok=True)
    (x11_jni/'libXlorie.so').write_bytes(native)
    manifest = {'applicationId': 'com.archoh', 'version':LOCK['version_name'], 'bootstrapBytes':output.stat().st_size, 'expandedBytes':sum(len(b) for b,m in files.values()), 'bootstrapSha256':hashlib.sha256(output.read_bytes()).hexdigest(), 'packages':{name:packages[name]['Version'] for name in sorted(wanted)}, 'sources':LOCK, 'termuxApkSha256':expected}
    (assets/'runtime-manifest.json').write_text(json.dumps(manifest, indent=2))
    print('Offline runtime:', len(wanted), 'packages,', output.stat().st_size, 'bytes')

if __name__ == '__main__':
    main()
