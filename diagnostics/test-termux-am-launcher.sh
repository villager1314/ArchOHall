#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
task_dir=$(mktemp -d)
trap 'rm -rf "$task_dir"' EXIT
mkdir -p "$task_dir/src/com/termux/termuxam" "$task_dir/classes"
cat > "$task_dir/src/com/termux/termuxam/FakeContext.java" <<'EOF'
package com.termux.termuxam;
public class FakeContext { public static String PACKAGE_NAME = "com.termux"; }
EOF
cat > "$task_dir/src/com/termux/termuxam/Am.java" <<'EOF'
package com.termux.termuxam;
public class Am {
    public static void main(String[] args) {
        if (!"com.archoh".equals(FakeContext.PACKAGE_NAME)) throw new AssertionError("wrong caller package");
        if (!java.util.Arrays.equals(args, new String[]{"broadcast", "--user", "0"})) throw new AssertionError("arguments changed");
        System.out.println("PASS: caller identity corrected before Am.main; arguments preserved");
    }
}
EOF
javac --release 8 -d "$task_dir/classes" "$source_dir/TermuxAmLauncher.java" "$task_dir/src/com/termux/termuxam/"*.java
PREFIX=/data/data/com.archoh/files/usr java -cp "$task_dir/classes" com.archoh.compat.TermuxAmLauncher broadcast --user 0
if PREFIX=/data/data/com.termux/files/usr java -cp "$task_dir/classes" com.archoh.compat.TermuxAmLauncher broadcast --user 0 > /dev/null 2>&1; then
    echo 'Launcher unexpectedly accepted another application' >&2; exit 1
fi
