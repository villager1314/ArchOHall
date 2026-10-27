#!/usr/bin/env python3
"""Sign distribution APKs with the retained ArchOHall key, never a runner key."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

CERT_SHA256 = '395043a9142654bea4cf43699c719dd77fd7276b4dc286f4399dfb273732de02'
SECRET_NAME = 'ARCHOHALL_SIGNING_BUNDLE'


def config():
    value = os.environ.get(SECRET_NAME, '')
    if not value:
        raise SystemExit(f'Missing repository secret {SECRET_NAME}; refusing temporary signing.')
    try:
        parsed = json.loads(value)
        alias, password = parsed['alias'], parsed['password']
        keystore = base64.b64decode(parsed['keystore_base64'], validate=True)
        if not isinstance(alias, str) or not alias or not isinstance(password, str) or not password or not keystore:
            raise ValueError()
        return alias, password, keystore
    except (ValueError, KeyError, TypeError):
        # Never echo secret values, including malformed JSON, in CI logs.
        raise SystemExit(f'Invalid {SECRET_NAME} configuration.') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-config', action='store_true')
    parser.add_argument('input_apk', nargs='?')
    parser.add_argument('output_apk', nargs='?')
    args = parser.parse_args()
    alias, password, keystore = config()
    if args.check_config:
        print('Fixed signing configuration is present.')
        return
    if not args.input_apk or not args.output_apk:
        parser.error('input_apk and output_apk are required')
    tools = Path(os.environ['ANDROID_HOME']) / 'build-tools/36.0.0'
    output = Path(args.output_apk)
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ARCHOHALL_KEY_PASSWORD=password)
    # Do not propagate the complete secret bundle to signing subprocesses.
    env.pop(SECRET_NAME, None)
    try:
        with tempfile.TemporaryDirectory(prefix='archohall-sign-', dir=os.environ.get('RUNNER_TEMP')) as directory:
            key = Path(directory) / 'signing.p12'
            key.write_bytes(keystore)
            key.chmod(0o600)
            subprocess.run([str(tools / 'apksigner'), 'sign', '--ks', str(key),
                            '--ks-key-alias', alias, '--ks-pass', 'env:ARCHOHALL_KEY_PASSWORD',
                            '--v1-signing-enabled', 'false', '--v2-signing-enabled', 'true',
                            '--v3-signing-enabled', 'true', '--out', str(output), args.input_apk],
                           env=env, check=True, capture_output=True)
            certs = subprocess.check_output([str(tools / 'apksigner'), 'verify', '--print-certs', str(output)], text=True)
            if f'Signer #1 certificate SHA-256 digest: {CERT_SHA256}' not in certs or 'Signer #2 ' in certs:
                raise ValueError('Signing certificate does not match the retained ArchOHall certificate.')
            subprocess.run([str(tools / 'zipalign'), '-c', '-P', '16', '4', str(output)], check=True, capture_output=True)
    except (subprocess.CalledProcessError, ValueError):
        output.unlink(missing_ok=True)
        raise SystemExit('Signing or certificate/alignment verification failed; no APK will be published.') from None
    print(f'Fixed signing and APK alignment verified. Certificate SHA-256: {CERT_SHA256}')


if __name__ == '__main__':
    main()
