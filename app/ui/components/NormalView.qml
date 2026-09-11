import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    function dp(px) { return controller.scaler.dp(px); }
    function sp(px) { return controller.scaler.sp(px); }

    // Top row: Status dot at x = dp(22), cy = dp(24)
    StatusDot {
        id: statusDot
        x: root.dp(22) - (width / 2)
        y: root.dp(24) - (height / 2)
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // Model name at x = dp(40), font=(FONT_NAME, 10, 'bold')
    Text {
        id: modelTitle
        x: root.dp(40)
        anchors.verticalCenter: statusDot.verticalCenter
        text: controller.latestModel
        color: "#ffffff"
        font.family: "SF Pro Display"
        font.pointSize: 10
        font.bold: true
        elide: Text.ElideRight
        width: timelineTabs.x - root.dp(40) - root.dp(14)
    }

    // Timeline Tabs at top right (rightMargin = dp(22))
    TimelineTabs {
        id: timelineTabs
        anchors.right: parent.right
        anchors.rightMargin: root.dp(22)
        anchors.verticalCenter: statusDot.verticalCenter
        currentTimeline: controller.timeline
        onTimelineSelected: function(key) {
            controller.setTimeline(key);
        }
    }

    // Middle row: "92.3M Tokens" at x = dp(22), cy = dp(64), font=(FONT_NAME, 16, 'bold')
    Text {
        id: bigTokens
        x: root.dp(22)
        y: root.dp(64) - (implicitHeight / 2)
        text: controller.totalTokensStr + " Tokens"
        color: "#ffffff"
        font.family: "SF Pro Display"
        font.pointSize: 16
        font.bold: true
    }

    // "$23.03 | 457 reqs" at x = w - dp(22), cy = dp(64), font=(FONT_NAME, 12, 'bold')
    Text {
        id: costAndReqs
        anchors.right: parent.right
        anchors.rightMargin: root.dp(22)
        anchors.baseline: bigTokens.baseline
        color: controller.flyingDeltaText !== "" ? "#30D158" : "#ffffff"
        font.family: "SF Pro Display"
        font.pointSize: 12
        font.bold: true
        text: controller.flyingDeltaText !== "" ? controller.flyingDeltaText : (controller.costStr + "  |  " + controller.requestsStr + " reqs")
    }

    // Bottom row: "Last: 1m ago • ..." at x = dp(22), cy = dp(104), font=(FONT_NAME, 9)
    Text {
        id: tickerLabel
        x: root.dp(22)
        y: root.dp(104) - (implicitHeight / 2)
        anchors.right: expandHint.left
        anchors.rightMargin: root.dp(12)
        text: controller.tickerText
        color: "#808080"
        font.family: "SF Pro Display"
        font.pointSize: 9
        elide: Text.ElideRight
    }

    // "Full" at x = w - dp(22), cy = dp(104), font=(FONT_NAME, 9, 'bold')
    Text {
        id: expandHint
        anchors.right: parent.right
        anchors.rightMargin: root.dp(22)
        anchors.verticalCenter: tickerLabel.verticalCenter
        text: "Full"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pointSize: 9
        font.bold: true
    }
}
