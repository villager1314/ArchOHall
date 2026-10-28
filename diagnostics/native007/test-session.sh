#!/usr/bin/env bash
set -euo pipefail
qdbus=$(command -v qdbus6 || command -v qdbus || echo /usr/lib/qt6/bin/qdbus)
export QT_QPA_PLATFORM=wayland
# The stock effect and its stock shortcut handler must be loadable.
for ((i=0;i<90;i++)); do
 if "$qdbus" org.kde.KWin /Effects org.kde.kwin.Effects.loadEffect mobiletaskswitcher > /native-results/load.txt 2>&1; then break; fi
 sleep 1
done
"$qdbus" org.kde.KWin /KWin org.kde.KWin.supportInformation > /native-results/support.txt
"$qdbus" org.kde.KWin /Effects org.kde.kwin.Effects.loadedEffects > /native-results/loaded.txt
grep -qi mobiletaskswitcher /native-results/loaded.txt
grep -qi OpenGL /native-results/support.txt
# Exercise the exact native invocation used by Plasma's square navigation key.
"$qdbus" org.kde.kglobalaccel /component/kwin org.kde.kglobalaccel.Component.invokeShortcut 'Mobile Task Switcher'
sleep 3
"$qdbus" org.kde.KWin /Effects org.kde.kwin.Effects.activeEffects > /native-results/active.txt
grep -qi mobiletaskswitcher /native-results/active.txt
"$qdbus" org.kde.kglobalaccel /component/kwin org.kde.kglobalaccel.Component.invokeShortcut 'Mobile Task Switcher'
sleep 2
"$qdbus" org.kde.KWin /Effects org.kde.kwin.Effects.activeEffects > /native-results/closed.txt
if grep -qi mobiletaskswitcher /native-results/closed.txt; then echo 'Native switcher did not close'; exit 1; fi
printf 'PASS: stock Mobile Task Switcher loaded, activated and dismissed through native KGlobalAccel\n' > /native-results/PASS
