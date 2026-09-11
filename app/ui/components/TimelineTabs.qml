import QtQuick

Row {
    id: root
    property string currentTimeline: "today"
    signal timelineSelected(string key)
    spacing: 4

    readonly property var tabs: [
        { "key": "today", "label": "Today" },
        { "key": "7d", "label": "7D" },
        { "key": "30d", "label": "30D" },
        { "key": "all", "label": "All" }
    ]

    Repeater {
        model: root.tabs
        Rectangle {
            id: tabBtn
            required property var modelData
            width: 38
            height: 20
            radius: 10
            color: root.currentTimeline === modelData.key ? "#2A2A2D" : "#121214"
            border.color: root.currentTimeline === modelData.key ? "#3C3C40" : "#202023"
            border.width: 1

            Behavior on color {
                ColorAnimation { duration: 120 }
            }

            Text {
                anchors.centerIn: parent
                text: tabBtn.modelData.label
                color: root.currentTimeline === tabBtn.modelData.key ? "#FFFFFF" : "#58585E"
                font.family: "SF Pro Display"
                font.pixelSize: 10
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.timelineSelected(tabBtn.modelData.key)
            }
        }
    }
}
