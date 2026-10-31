#!/usr/bin/env python3
"""Reuse Portal's damage transport; compile typed KWin 6.8 hooks separately."""
import argparse
import hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('upstream',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
raw=a.upstream.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='aefba6323fcd1836d61b5f133b1b300d79bc49af16a32c0832b1c3b3aa866f5e','Unexpected upstream damage shim'
s=raw.decode()
# Socket reconnection, 2 ms limiting, errno handling and clock code unchanged.
transport=s[s.index('static int hint_fd'):s.index('__attribute__((visibility("default")))')]
a.output.mkdir(parents=True,exist_ok=True)
api='''#pragma once
#include <chrono>
#include <optional>
namespace KWin {
class Item;
using Deadline = std::optional<std::chrono::steady_clock::time_point>;
class OutputLayer;
class RenderLoop { public: void scheduleRepaint(Item *, OutputLayer *, Deadline = std::nullopt); };
class OutputLayer { public: void scheduleRepaint(Item *, Deadline = std::nullopt); };
}
'''
(a.output/'kwin-api.hpp').write_text(api)
(a.output/'symbols.cpp').write_text('#include "kwin-api.hpp"\nvoid KWin::RenderLoop::scheduleRepaint(Item *, OutputLayer *, Deadline) {}\nvoid KWin::OutputLayer::scheduleRepaint(Item *, Deadline) {}\n')
source='''// Transport derived verbatim from pinned Portal anland-damage.c.
// Hooks adapted for KWin 6.8; definitions below do not access object layouts.
#include "kwin-api.hpp"
#include "symbols.hpp"
#include <cerrno>
#include <cstring>
#include <cstdlib>
#include <cstddef>
#include <sys/socket.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>
#include <dlfcn.h>
#include <cstdio>
#include <cstdint>
'''+transport+'''
// KWin's Anland endFrame calls OutputLayer::scheduleRepaint(nullptr) to
// catch up its buffer ring. Suppress hints from that call chain, without
// suppressing actual device damage (addDeviceRepaint -> RenderLoop directly).
static thread_local unsigned muting_catch_up;
static void missing_original(const char *symbol) {
    std::fprintf(stderr, "ArchOHall damage shim: missing original %s\\n", symbol);
    std::abort(); // Never silently swallow a compositor repaint.
}
void KWin::RenderLoop::scheduleRepaint(Item *item, OutputLayer *layer, Deadline deadline) {
    using Fn = void (*)(RenderLoop *, Item *, OutputLayer *, Deadline);
    static Fn original = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, RENDERLOOP_SYMBOL));
    if (!original) missing_original(RENDERLOOP_SYMBOL);
    if (!muting_catch_up && (item || layer)) damage_hint();
    original(this, item, layer, deadline);
}
void KWin::OutputLayer::scheduleRepaint(Item *item, Deadline deadline) {
    using Fn = void (*)(OutputLayer *, Item *, Deadline);
    static Fn original = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, OUTPUTLAYER_SYMBOL));
    if (!original) missing_original(OUTPUTLAYER_SYMBOL);
    const bool internal = item == nullptr;
    muting_catch_up += internal;
    original(this, item, deadline);
    muting_catch_up -= internal;
}
'''
(a.output/'anland-damage-68.cpp').write_text(source)
print('Generated KWin 6.8 hooks; reused pinned upstream transport without edits')
