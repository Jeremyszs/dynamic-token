import QtQuick

Row {
    id: root
    property string currentTimeline: "today"
    signal timelineSelected(string key)
    spacing: controller ? controller.scaler.dp(4) : 4

    function dp(px) { return controller ? controller.scaler.dp(px) : px; }
    function sp(px) { return controller ? controller.scaler.sp(px) : px; }

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
            width: tabText.implicitWidth + root.dp(14)
            height: root.dp(20)
            radius: root.dp(6)
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
                font.pointSize: 8
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
