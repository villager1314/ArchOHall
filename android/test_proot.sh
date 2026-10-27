#!/usr/bin/env bash
# Test the same Termux PRoot fork/version shipped in the offline runtime.
# Ubuntu's older upstream PRoot has different setuid emulation semantics.
set -euo pipefail
task_proot_dir="${RUNNER_TEMP:-/tmp}/archohall-test-proot"
mkdir -p "$task_proot_dir"
curl -fL --retry 4 --connect-timeout 30 --max-time 300 \
    https://github.com/termux/proot/archive/v5.1.107.101.zip -o "$task_proot_dir/source.zip"
echo "a66743f50c7b0bac1913b83bf55e139d679c80a0ca2808eec76432a65640017f  $task_proot_dir/source.zip" | sha256sum -c -
unzip -q "$task_proot_dir/source.zip" -d "$task_proot_dir"
make -C "$task_proot_dir/proot-5.1.107.101/src" -j2
export ARCHOHALL_TEST_PROOT="$task_proot_dir/proot-5.1.107.101/src/proot"
python3 -m unittest discover -s tests -v
