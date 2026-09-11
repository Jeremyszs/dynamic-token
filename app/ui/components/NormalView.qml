import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // Top row: Status dot at x=14, y=10
    StatusDot {
        id: statusDot
        x: 14
        y: 12
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // Model name at x=34, font size 14 bold white
    Text {
        id: modelTitle
        x: 34
        anchors.verticalCenter: statusDot.verticalCenter
        text: controller.latestModel
        color: "#ffffff"
        font.family: "SF Pro Display"
        font.pixelSize: 14
        font.bold: true
        elide: Text.ElideRight
        width: timelineTabs.x - 34 - 12
    }

    // Timeline Tabs at top right
    TimelineTabs {
        id: timelineTabs
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: statusDot.verticalCenter
        currentTimeline: controller.timeline
        onTimelineSelected: function(key) {
            controller.setTimeline(key);
        }
    }

    // Middle row (pady=4): Primary Metrics
    // "92.3M Tokens" on left at x=14, y=44 (font size 22 bold)
    Text {
        id: bigTokens
        x: 14
        y: 44
        text: controller.totalTokensStr + " Tokens"
        color: "#ffffff"
        font.family: "SF Pro Display"
        font.pixelSize: 22
        font.bold: true
    }

    // "$23.03 | 457 reqs" on right at x=w-14, y=48 (font size 16 bold)
    Text {
        id: costAndReqs
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.baseline: bigTokens.baseline
        color: controller.flyingDeltaText !== "" ? "#30D158" : "#ffffff"
        font.family: "SF Pro Display"
        font.pixelSize: 16
        font.bold: true
        text: controller.flyingDeltaText !== "" ? controller.flyingDeltaText : (controller.costStr + " | " + controller.requestsStr + " reqs")
    }

    // Bottom row: Secondary telemetry
    // "Last: 1m ago • gemini-3.8-flash-high • +390.4k tok • 22.9s • 183 tok/s" (font size 11, #808080)
    Text {
        id: tickerLabel
        x: 14
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        anchors.right: expandHint.left
        anchors.rightMargin: 12
        text: controller.tickerText
        color: "#808080"
        font.family: "SF Pro Display"
        font.pixelSize: 11
        elide: Text.ElideRight
    }

    // "Full" on right at x=w-14
    Text {
        id: expandHint
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: tickerLabel.verticalCenter
        text: "Full"
        color: "#808080"
        font.family: "SF Pro Display"
        font.pixelSize: 11
    }
}
