import QtQuick

Row {
    id: root
    property string currentTimeline: "today"
    signal timelineSelected(string key)
    spacing: 3

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
            width: tabText.implicitWidth + 14
            height: 20
            radius: 5
            color: root.currentTimeline === modelData.key ? "#2a2a2a" : "#111111"
            border.color: root.currentTimeline === modelData.key ? "#404040" : "#1a1a1a"
            border.width: 1

            Behavior on color {
                ColorAnimation { duration: 120 }
            }

            Text {
                id: tabText
                anchors.centerIn: parent
                text: tabBtn.modelData.label
                color: root.currentTimeline === tabBtn.modelData.key ? "#ffffff" : "#666666"
                font.family: "SF Pro Display"
                font.pixelSize: 11
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
