#!/usr/bin/env python3
"""Compare every X11 native Java declaration against the official JNI donor APK.

Read DEX directly so this check needs neither an Android device nor a decompiler.
This catches ABI mismatches before JNI RegisterNatives aborts the app process.
"""
import re
import struct
import sys
import zipfile


def declarations(data):
    def u32(offset):
        return struct.unpack_from('<I', data, offset)[0]

    def uleb(offset):
        value = shift = 0
        while True:
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if not byte & 128:
                return value, offset
            shift += 7

    if not data.startswith(b'dex\n'):
        raise ValueError('Expected a standard DEX file')
    strings = []
    for i in range(u32(56)):
        _, offset = uleb(u32(u32(60) + 4 * i))
        strings.append(data[offset:data.index(b'\0', offset)].decode('utf-8', errors='replace'))
    types = [strings[u32(u32(68) + 4 * i)] for i in range(u32(64))]
    protos = []
    for i in range(u32(72)):
        _, result, offset = struct.unpack_from('<III', data, u32(76) + 12 * i)
        args = '' if not offset else ''.join(types[struct.unpack_from('<H', data, offset + 4 + 2*j)[0]] for j in range(u32(offset)))
        protos.append('(' + args + ')' + types[result])
    methods = []
    for i in range(u32(88)):
        cls, proto, name = struct.unpack_from('<HHI', data, u32(92) + 8 * i)
        methods.append((types[cls], strings[name], protos[proto]))
    native = set()
    for i in range(u32(96)):
        base = u32(100) + 32 * i
        offset = u32(base + 24)
        if not offset or not types[u32(base)].startswith('Lcom/termux/x11/'):
            continue
        sizes = []
        for _ in range(4):
            value, offset = uleb(offset)
            sizes.append(value)
        for _ in range(sizes[0] + sizes[1]):
            _, offset = uleb(offset)
            _, offset = uleb(offset)
        for count in sizes[2:]:
            index = 0
            for _ in range(count):
                delta, offset = uleb(offset)
                flags, offset = uleb(offset)
                _, offset = uleb(offset)
                index += delta
                if flags & 0x100:
                    native.add((*methods[index], bool(flags & 8)))
    return native


def apk_declarations(path):
    found = set()
    with zipfile.ZipFile(path) as apk:
        for name in apk.namelist():
            if re.fullmatch(r'classes\d*\.dex', name):
                found.update(declarations(apk.read(name)))
    if not found:
        raise ValueError(f'No X11 native declarations in {path}')
    return found


def verify_native_zip(path):
    # Unlike Activity System.loadLibrary, app_process loads the APK entry directly.
    # An installed/extracted copy cannot compensate for a compressed APK entry.
    count = 0
    with zipfile.ZipFile(path) as apk, open(path, 'rb') as raw:
        for item in apk.infolist():
            if not item.filename.startswith('lib/arm64-v8a/') or not item.filename.endswith('.so'):
                continue
            if item.compress_type != zipfile.ZIP_STORED:
                raise SystemExit(f'Native APK entry must be uncompressed for app_process dlopen: {item.filename}')
            raw.seek(item.header_offset + 26)
            name_length, extra_length = struct.unpack('<HH', raw.read(4))
            offset = item.header_offset + 30 + name_length + extra_length
            if offset % 16384:
                raise SystemExit(f'Native APK entry is not 16 KiB aligned: {item.filename} at {offset}')
            count += 1
    if not count:
        raise SystemExit('No ARM64 native APK entries found')
    print(f'Validated {count} uncompressed, 16 KiB aligned ARM64 native APK entries.')


def main():
    expected, actual = map(apk_declarations, sys.argv[1:])
    if expected != actual:
        raise SystemExit('X11 JNI mismatch!\nMissing: ' + repr(sorted(expected-actual)) + '\nUnexpected: ' + repr(sorted(actual-expected)))
    print(f'Validated {len(expected)} X11 native method names, descriptors and static flags against the official APK.')
    verify_native_zip(sys.argv[2])


if __name__ == '__main__':
    main()
