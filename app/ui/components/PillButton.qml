import QtQuick

Rectangle {
    id: root
    property alias text: label.text
    property alias font: label.font
    property color textColor: "#FFFFFF"
    property color normalColor: "#1C1C1F"
    property color hoverColor: "#28282C"
    property color pressColor: "#141416"
    property color borderColor: "#333338"
    property int buttonRadius: 8
    signal clicked()

    implicitHeight: 24
    implicitWidth: label.implicitWidth + 16
    radius: buttonRadius
    color: mouseArea.pressed ? pressColor : (mouseArea.containsMouse ? hoverColor : normalColor)
    border.color: borderColor
    border.width: 1

    Behavior on color {
        ColorAnimation { duration: 120 }
    }

    Text {
        id: label
        anchors.centerIn: parent
        color: root.textColor
        font.family: "SF Pro Display"
        font.pixelSize: 10
        font.bold: true
        elide: Text.ElideRight
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
