#!/usr/bin/env python3
"""Generate auditable GenericQML replacements; retain upstream quick-setting IDs."""
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEST = REPO / 'rootfs/usr/local/share/archohall/quicksettings'

JS = '''.pragma library
function read(callback) {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            try { var s = JSON.parse(xhr.responseText); callback(s.schema === 1 && Math.abs(Date.now()-s.timestamp) < 15000 ? s : {}); }
            catch(e) { callback({}); }
        }
    };
    xhr.open("GET", "file:///run/archohall-host/state.json");
    xhr.send();
}
'''

# title, icon, displayed status, highlighted state, whitelisted host action
TILES = {
 'wifi': ('Wi-Fi', 'network-wireless', 'host.wifi === undefined || host.wifi === null ? "打开 Android 网络面板" : (host.wifi ? "已开启 · 点击管理" : "已关闭 · 点击管理")', 'host.wifi === true', 'wifi'),
 'mobiledata': ('移动数据', 'network-mobile', 'host.network === "mobile" ? "正在使用 · 点击管理" : "打开 Android 网络设置"', 'host.network === "mobile"', 'mobiledata'),
 'bluetooth': ('蓝牙', 'preferences-system-bluetooth', 'host.bluetooth === null ? "打开 Android 蓝牙设置" : (host.bluetooth ? "已开启 · 点击管理" : "已关闭 · 点击管理")', 'host.bluetooth === true', 'bluetooth'),
 'airplanemode': ('飞行模式', 'network-flightmode-on', 'host.airplane ? "已开启 · 点击管理" : "已关闭 · 点击管理"', 'host.airplane === true', 'airplane'),
 'hotspot': ('热点', 'network-wireless-hotspot', '"打开 Android 热点设置"', 'false', 'hotspot'),
 'androidsettings': ('Android 设置', 'configure', '"打开手机系统设置"', 'false', 'settings'),
 'audio': ('声音', 'audio-volume-high', 'host.volumeMax > 0 ? Math.round(host.volume*100/host.volumeMax)+"% · Android 媒体音量" : "打开媒体音量"', 'false', 'volume'),
 'battery': ('电池', 'battery-full', 'host.battery === null || host.battery === undefined ? "电量未知" : host.battery+"%"+(host.plugged ? " · 正在供电" : "")', 'host.plugged === true', 'battery'),
 'caffeine': ('保持亮屏', 'system-suspend-hibernate', 'host.keepAwake ? "ArchOHall 窗口保持亮屏" : "点击保持桌面亮屏"', 'host.keepAwake === true', 'keepawake'),
 'nightcolor': ('护眼色温', 'redshift-status-on', 'host.nightTint ? "窗口暖色滤镜已开启" : "点击开启窗口暖色滤镜"', 'host.nightTint === true', 'nightcolor'),
 'donotdisturb': ('勿扰模式', 'notifications-disabled', '!host.dndGranted ? "点击打开勿扰授权" : (host.dnd ? "Android 勿扰已开启" : "Android 勿扰已关闭")', 'host.dnd === true', 'dnd'),
 'powermenu': ('停止桌面', 'system-shutdown', '"关闭 Linux 桌面，保留数据"', 'false', 'power'),
 'waydroid': ('Android 应用', 'android', '"打开手机已安装的应用"', 'false', 'apps'),
 'brightness': ('窗口亮度', 'brightness-high', 'host.brightness < 0 ? "跟随系统 · 点击调节" : Math.round(host.brightness*100)+"% · 仅桌面窗口"', 'false', 'brightness'),
}


def main():
    if DEST.exists(): shutil.rmtree(DEST)
    DEST.mkdir(parents=True, exist_ok=True)
    for key, (title, icon, status, enabled, action) in TILES.items():
        prefix = 'org.archohall.quicksetting.' if key in ('brightness','androidsettings') else 'org.kde.plasma.quicksetting.'
        plugin = prefix + key
        directory = DEST / plugin
        ui = directory / 'contents/ui'
        ui.mkdir(parents=True, exist_ok=True)
        (directory/'metadata.json').write_text(json.dumps({'KPackageStructure':'KPackage/GenericQML', 'KPlugin':{'Id':plugin,'Name':title,'Description':'ArchOHall Android host bridge','Icon':icon,'License':'GPL-3.0-or-later','Version':'0.07'}}, ensure_ascii=False,indent=2)+'\n')
        (ui/'bridge.js').write_text(JS)
        (ui/'main.qml').write_text(f'''// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import org.kde.plasma.private.mobileshell.quicksettingsplugin as QS
import org.kde.plasma.private.mobileshell as MobileShell
import org.kde.plasma.private.mobileshell.state as MobileShellState
import "bridge.js" as Bridge

QS.QuickSetting {{
    id: root
    property var host: ({{}})
    text: {json.dumps(title,ensure_ascii=False)}
    icon: "{icon}"
    status: host.schema === 1 ? ({status}) : "Android 桥接未连接"
    enabled: host.schema === 1 && ({enabled})
    settingsCommand: "/usr/local/bin/archohall-host {action}"
    Component.onCompleted: Bridge.read(function(s) {{ root.host = s; }})
    Timer {{ interval: 2000; running: true; repeat: true; onTriggered: Bridge.read(function(s) {{ root.host = s; }}) }}
    function toggle() {{
        MobileShellState.ShellDBusClient.closeActionDrawer();
        MobileShell.ShellUtil.executeCommand("/usr/local/bin/{'archohall-controls' if key in ('audio', 'brightness') else 'archohall-host'} {action}");
    }}
}}
''')
    controls = REPO / 'rootfs/usr/local/share/archohall/controls'
    controls.mkdir(parents=True, exist_ok=True)
    (controls/'bridge.js').write_text(JS)
    for control, title in [('volume', 'Android 媒体音量'), ('brightness', '桌面窗口亮度')]:
        initial = '(host.volumeMax > 0 ? host.volume*100/host.volumeMax : 0)' if control == 'volume' else '(host.brightness >= 0 ? host.brightness*100 : 50)'
        (controls/('Volume.qml' if control == 'volume' else 'Brightness.qml')).write_text(f'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.plasma.private.mobileshell as MobileShell
import "bridge.js" as Bridge
ApplicationWindow {{
    id: root
    visible: true
    width: 420
    height: 240
    title: "{title}"
    property var host: ({{}})
    Component.onCompleted: Bridge.read(function(s) {{ root.host = s; slider.value = {initial}; }})
    ColumnLayout {{
        anchors.fill: parent
        anchors.margins: 24
        Label {{ text: root.title; font.pixelSize: 20 }}
        Label {{ text: "{('调节手机媒体音量' if control == 'volume' else '仅影响 ArchOHall 桌面窗口')}"; wrapMode: Text.Wrap; Layout.fillWidth: true }}
        Slider {{
            id: slider
            Layout.fillWidth: true
            from: {('0' if control == 'volume' else '2')}
            to: 100
            stepSize: 1
            enabled: root.host.numericControls === true
            onMoved: debounce.restart()
        }}
        Label {{ text: root.host.numericControls === true ? Math.round(slider.value) + "%" : "Android 桥接未连接或版本过旧" }}
        Button {{ text: "关闭"; onClicked: root.close() }}
    }}
    Timer {{
        id: debounce
        interval: 150
        onTriggered: MobileShell.ShellUtil.executeCommand("/usr/local/bin/archohall-host {control}-set " + Math.round(slider.value))
    }}
    onClosing: Qt.quit()
}}
''')
    for key,title,icon in [('screenshot','屏幕截图','view-fullscreen-symbolic'),('record','录制 Linux 桌面','camera-video-symbolic')]:
        plugin='org.kde.plasma.quicksetting.'+key
        directory=DEST/plugin;ui=directory/'contents/ui';ui.mkdir(parents=True,exist_ok=True)
        (directory/'metadata.json').write_text(json.dumps({'KPackageStructure':'KPackage/GenericQML','KPlugin':{'Id':plugin,'Name':title,'Description':'Linux X11 capture; no Android display access','Icon':icon,'License':'GPL-3.0-or-later','Version':'0.07'}},ensure_ascii=False,indent=2)+'\n')
        command='screenshot' if key=='screenshot' else 'toggle'
        (ui/'main.qml').write_text(f'''// SPDX-License-Identifier: GPL-3.0-or-later
import org.kde.plasma.private.mobileshell.quicksettingsplugin as QS
import org.kde.plasma.private.mobileshell as MobileShell
import org.kde.plasma.private.mobileshell.state as MobileShellState
QS.QuickSetting {{
    text: {json.dumps(title,ensure_ascii=False)}
    icon: "{icon}"
    status: {json.dumps('保存到 Pictures/ArchOHall' if key=='screenshot' else '点击开始/停止 · Videos/ArchOHall · 无麦克风',ensure_ascii=False)}
    enabled: false
    function toggle() {{
        MobileShellState.ShellDBusClient.closeActionDrawer();
        MobileShell.ShellUtil.executeCommand("/usr/local/bin/archohall-capture {command}");
    }}
}}
''')


if __name__ == '__main__': main()
