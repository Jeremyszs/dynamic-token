import QtQuick

Item {
    id: root
    property real cornerRadius: 21
    property bool isDockedNotch: false
    property bool isHovered: false
    property bool isActivityActive: false
    property bool isActivityError: false

    Rectangle {
        id: bgRect
        anchors.fill: parent
        color: "#000000"
        radius: root.cornerRadius

        border.color: root.isHovered ? "#444448" : "#262629"
        border.width: 1

        Behavior on border.color {
            ColorAnimation { duration: 150 }
        }

        // When docked notch is true, square off top corners seamlessly
        Rectangle {
            id: topFlattenSquare
            visible: root.isDockedNotch
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: root.cornerRadius
            color: "#000000"

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                width: 1
                color: root.isHovered ? "#444448" : "#262629"
            }
            Rectangle {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                width: 1
                color: root.isHovered ? "#444448" : "#262629"
            }
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: root.isHovered ? "#444448" : "#262629"
            }
        }
    }

    // Specular Activity Rim Glow (Apple neon perimeter beam)
    Rectangle {
        id: rimGlow
        anchors.fill: parent
        radius: root.cornerRadius
        color: "transparent"
        border.color: root.isActivityError ? "#FF453A" : "#30D158"
        border.width: 2
        opacity: root.isActivityActive ? 0.75 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 300; easing.type: Easing.OutQuad }
        }
    }
}
