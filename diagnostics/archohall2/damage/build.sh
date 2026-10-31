#!/usr/bin/env bash
# Native build. On an ARM64 runner this produces the actual guest ARM64 library.
set -euo pipefail
upstream=${1:?upstream anland-damage.c}
out=${2:?output directory}
mkdir -p "$out"
python3 "$(dirname "$0")/generate.py" "$upstream" "$out"
"${CXX:-g++}" -std=c++20 -fPIC -c "$out/symbols.cpp" -o "$out/symbols.o"
python3 - "$out" <<'PY'
from pathlib import Path
import subprocess,sys,json
out=Path(sys.argv[1]);symbols=subprocess.check_output(['nm','--defined-only',str(out/'symbols.o')],text=True)
records=[]
for macro,prefix in [('RENDERLOOP_SYMBOL','_ZN4KWin10RenderLoop15scheduleRepaintE'),('OUTPUTLAYER_SYMBOL','_ZN4KWin11OutputLayer15scheduleRepaintE')]:
 names=[line.split()[-1] for line in symbols.splitlines() if line.split()[-1].startswith(prefix)]
 assert len(names)==1,(macro,names)
 records.append(f'#define {macro} {json.dumps(names[0])}\n')
(out/'symbols.hpp').write_text(''.join(records))
(out/'required-symbols.txt').write_text(''.join(line.split()[-1]+'\n' for line in symbols.splitlines() if 'scheduleRepaintE' in line))
PY
"${CXX:-g++}" -std=c++20 -O2 -fPIC -shared -fno-exceptions -fno-rtti \
    -Wall -Wextra -Werror -Wl,-z,defs -Wl,-z,max-page-size=16384 \
    -Wl,-soname,anland-damage-68.so "$out/anland-damage-68.cpp" \
    -o "$out/anland-damage-68.so" -ldl
readelf -h "$out/anland-damage-68.so" > "$out/elf-header.txt"
readelf -d "$out/anland-damage-68.so" > "$out/elf-dynamic.txt"
sha256sum "$out/anland-damage-68.so" > "$out/SHA256SUMS"
