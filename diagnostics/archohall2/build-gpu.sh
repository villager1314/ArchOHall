#!/usr/bin/env bash
# Native Arch ARM64 GPU payload, matching the reused Arch desktop checkpoint.
set -euo pipefail
pacman-key --init
pacman-key --populate archlinuxarm
pacman -Syu --needed --noconfirm --disable-sandbox base-devel meson ninja cmake ccache \
    python-mako python-pyyaml python-packaging python-ply python-setuptools \
    libdrm libx11 libxext libxdamage libxfixes libxrandr libxshmfence libxxf86vm \
    libxcb xcb-proto xorgproto wayland wayland-protocols libglvnd \
    libelf libarchive zlib zstd bison flex git rust rust-bindgen vulkan-headers python-pycparser python-jinja
python /input/verify-packages.py
export CCACHE_DIR=/input/ccache CCACHE_COMPILERCHECK=content
export CC='ccache gcc' CXX='ccache g++'
ccache --max-size=2G
trap 'ccache --show-stats > /output/gpu-ccache.txt || true' EXIT
src=/input/mesa
for patch in /input/portal/patches/mesa/kgsl-layer-26.3.0/[0-9][0-9][0-9][0-9]-*.patch; do
    git -c safe.directory="$src" -C "$src" apply --check "$patch"
    git -c safe.directory="$src" -C "$src" apply "$patch"
done
meson setup /input/mesa-build "$src" --prefix=/opt/archohall-mobile --libdir=lib \
    -Dplatforms=x11,wayland -Dgallium-drivers=freedreno -Dvulkan-drivers=freedreno \
    -Dgallium-va=disabled -Dgallium-mediafoundation=disabled -Dvulkan-layers= \
    -Degl=enabled -Dgles2=enabled -Dglvnd=enabled -Dglx=dri -Dllvm=disabled \
    -Dlibunwind=disabled -Dintel-rt=disabled -Dmicrosoft-clc=disabled \
    -Dvalgrind=disabled -Dgles1=disabled -Dfreedreno-kmds=kgsl -Dbuildtype=release
meson compile -C /input/mesa-build -j 4
DESTDIR=/output/gpu-staging meson install -C /input/mesa-build
lib=/output/gpu-staging/opt/archohall-mobile/lib
ccache gcc -shared -fPIC -O2 -Wl,-z,max-page-size=16384 \
    /input/portal/assets/guest-arm64/drmshim.c -o "$lib/drmshim.so" -ldl -pthread
# EGL JSON must resolve to this payload, never the stock Mesa library.
python - <<'PY'
import json
from pathlib import Path
p=Path('/output/gpu-staging/opt/archohall-mobile/share/glvnd/egl_vendor.d/50_mesa.json')
s=json.loads(p.read_text());s['ICD']['library_path']='/opt/archohall-mobile/lib/libEGL_mesa.so.0';p.write_text(json.dumps(s)+'\n')
PY
for p in "$lib"/libEGL_mesa.so.0 "$lib"/libgbm.so.1 "$lib"/drmshim.so; do
    LD_LIBRARY_PATH="$lib" ldd "$p" | tee -a /output/gpu-ldd.txt
done
! grep -q 'not found' /output/gpu-ldd.txt
pacman -Q > /output/gpu-build-packages.txt
tar --zstd -cpf /output/archohall2-gpu.tar.zst -C /output/gpu-staging .
(cd /output && sha256sum archohall2-gpu.tar.zst > archohall2-gpu.sha256)
