// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.taskmanager as TaskManager

ApplicationWindow {
    id: root
    visible: true
    width: 480
    height: 640
    title: "ArchOHall 多任务"
    onClosing: Qt.quit()

    TaskManager.TasksModel {
        id: tasks
        filterByVirtualDesktop: false
        filterByActivity: false
        filterByScreen: false
        filterHidden: false
        groupMode: TaskManager.TasksModel.GroupDisabled
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        RowLayout {
            Layout.fillWidth: true
            Label { text: "正在运行的应用"; font.pixelSize: 22; Layout.fillWidth: true }
            Button { text: "返回"; onClicked: root.close() }
        }
        Label {
            visible: list.count === 0
            text: "没有正在运行的应用"
            Layout.alignment: Qt.AlignHCenter
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: tasks
            delegate: RowLayout {
                required property int index
                required property var model
                width: list.width
                visible: model.display !== root.title
                height: visible ? 64 : 0
                Button {
                    text: model.display || model.AppName || "应用窗口"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    onClicked: {
                        tasks.requestActivate(tasks.makeModelIndex(index));
                        root.close();
                    }
                }
                Button {
                    text: "关闭"
                    enabled: model.IsClosable === true
                    onClicked: tasks.requestClose(tasks.makeModelIndex(index))
                }
            }
        }
    }
}
