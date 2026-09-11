import QtQuick

Item {
    id: root
    property bool active: false
    property bool error: false
    width: 20
    height: 20

    // Subtle outer halo ring
    Rectangle {
        id: halo
        anchors.centerIn: parent
        width: 14
        height: 14
        radius: 7
        color: root.error ? "#FF453A" : "#30D158"
        opacity: root.active ? 0.35 : 0.08

        SequentialAnimation on opacity {
            running: root.active
            loops: Animation.Infinite
            NumberAnimation { to: 0.6; duration: 900; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.2; duration: 900; easing.type: Easing.InOutSine }
        }

        Behavior on color {
            ColorAnimation { duration: 200 }
        }
    }

    // Solid inner core
    Rectangle {
        id: core
        anchors.centerIn: parent
        width: 8
        height: 8
        radius: 4
        color: root.error ? "#FF453A" : "#30D158"

        Behavior on color {
            ColorAnimation { duration: 200 }
        }
    }
}
