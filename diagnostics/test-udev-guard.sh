#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
task_dir="$(mktemp -d)"
trap 'rm -rf "$task_dir"' EXIT
cat > "$task_dir/mock.cpp" <<'EOF'
#include <cstring>
namespace KWin {
class UdevMonitor {
public:
    int fd() const;
    void filterSubsystemDevType(const char *, const char *);
    void enable();
    int calls;
};
int UdevMonitor::fd() const { return calls + 40; }
void UdevMonitor::filterSubsystemDevType(const char *s, const char *t) {
    if (std::strcmp(s, "drm") == 0 && t == nullptr) ++calls;
}
void UdevMonitor::enable() { calls += 2; }
}
EOF
cat > "$task_dir/test.c" <<'EOF'
#include <assert.h>
#include <stddef.h>
int fd(const void *) __asm__("_ZNK4KWin11UdevMonitor2fdEv");
void filter(void *, const char *, const char *) __asm__("_ZN4KWin11UdevMonitor22filterSubsystemDevTypeEPKcS2_");
void enable(void *) __asm__("_ZN4KWin11UdevMonitor6enableEv");
int main(void) {
    assert(fd(NULL) == -1);
    filter(NULL, "drm", NULL);
    enable(NULL);
    int calls = 0;
    assert(fd(&calls) == 40);
    filter(&calls, "drm", NULL);
    enable(&calls);
    assert(calls == 3);
    assert(fd(&calls) == 43);
}
EOF
g++ -Wall -Wextra -Werror -fPIC -shared "$task_dir/mock.cpp" -o "$task_dir/libmock.so"
gcc -std=c11 -Wall -Wextra -Werror -O2 -fPIC -shared "$source_dir/kwin-udev-guard.c" -ldl -o "$task_dir/guard.so"
gcc -Wall -Wextra -Werror "$task_dir/test.c" -L"$task_dir" -lmock -Wl,-rpath,"$task_dir" -o "$task_dir/test"
LD_PRELOAD="$task_dir/guard.so" "$task_dir/test"
echo 'PASS: null monitor guarded; valid monitor fd/filter/enable forwarded to original C++ symbols'
