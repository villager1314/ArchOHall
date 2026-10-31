# KWin 6.8 damage-hint experiment

Transport is extracted unchanged from Portal's pinned `anland-damage.c`
(commit `9dff54c749c60b1eaf07e42b9f4e8de41e85af0a`, source SHA-256
`aefba6323fcd1836d61b5f133b1b300d79bc49af16a32c0832b1c3b3aa866f5e`).
This is a derivative of that GPL-3.0 project; retain its license/attribution.

Only the KWin-facing hooks change. C++ generates the real signatures and mangled
names for `RenderLoop::scheduleRepaint(Item*, OutputLayer*, optional<time_point>)`
and `OutputLayer::scheduleRepaint(Item*, optional<time_point>)`. No manual object
layout access or guessed representation of std::optional is used.

In this exact ported KWin source, Anland `endFrame()` catches up its buffer ring
by calling `OutputLayer::scheduleRepaint(nullptr)`. The preload mutes notifications
inside that call chain, while still invoking the original functions. Ordinary
scene-item repaints and direct device damage notify Android as before. Consumer
per-select `RenderLoop::scheduleRepaint()` has null pointers and does not notify.
No Qt Region object is inspected; the obsolete QRegion hook is not loaded.

The native test library simulates those call chains and verifies both present and
empty deadlines, original calls, content/damage hints, 1,000 suppressed catch-up
calls, rate limiting and an absent listener. Local sandbox prohibits AF_UNIX,
so local tests mock only transport syscalls. The dedicated ARM64 workflow runs
the same test with a real Unix datagram socket, then checks the actual existing
KWin binary's exported symbols and preemptible relocations.

No KWin, Mesa, rootfs or APK rebuild is part of this experiment. The ARM64 shared
library is not automatically installed or preloaded into an APK. A successful
symbol/test result is eligibility evidence, not on-device rendering acceptance.
Before enabling, check dependencies against Arch and compare animations/idle
frame activity on device. Inlined/uninterposed calls and other null-item repaint
sources need device-level pacing observation; do not claim complete hook coverage
from symbol presence alone. An incompatible/missing component keeps the existing
Anland heartbeat path instead of loading the old KWin 6.3 shim.
