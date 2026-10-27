// SPDX-License-Identifier: MIT
// Opt-in workaround for KWin GpuManager calling methods on a null UdevMonitor.
// Load ONLY into guest kwin_wayland, never Android or the host PRoot process.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>

static void *original(const char *symbol)
{
    dlerror();
    void *result = dlsym(RTLD_NEXT, symbol);
    const char *error = dlerror();
    if (error || !result) {
        fprintf(stderr, "ARCHOHALL_UDEV_GUARD: cannot resolve %s: %s\n",
                symbol, error ? error : "missing symbol");
        _exit(127);
    }
    return result;
}

// C entry points intentionally accept an ordinary pointer: testing a null C++
// 'this' inside a member function would be undefined and may be optimized away.
int monitor_fd(const void *monitor) __asm__("_ZNK4KWin11UdevMonitor2fdEv");
int monitor_fd(const void *monitor)
{
    if (!monitor) {
        fprintf(stderr, "ARCHOHALL_UDEV_GUARD: null UdevMonitor; hotplug monitoring disabled\n");
        // Qt leaves a QSocketNotifier with an invalid descriptor disabled.
        return -1;
    }
    typedef int (*function)(const void *);
    return ((function)original("_ZNK4KWin11UdevMonitor2fdEv"))(monitor);
}

void monitor_filter(void *monitor, const char *subsystem, const char *type)
    __asm__("_ZN4KWin11UdevMonitor22filterSubsystemDevTypeEPKcS2_");
void monitor_filter(void *monitor, const char *subsystem, const char *type)
{
    if (!monitor) return;
    typedef void (*function)(void *, const char *, const char *);
    ((function)original("_ZN4KWin11UdevMonitor22filterSubsystemDevTypeEPKcS2_"))(monitor, subsystem, type);
}

void monitor_enable(void *monitor) __asm__("_ZN4KWin11UdevMonitor6enableEv");
void monitor_enable(void *monitor)
{
    if (!monitor) return;
    typedef void (*function)(void *);
    ((function)original("_ZN4KWin11UdevMonitor6enableEv"))(monitor);
}
