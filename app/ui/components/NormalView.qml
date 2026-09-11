import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // Row 1: Status Dot, Model Name, Timeline Tabs
    Row {
        id: topRow
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.top: parent.top
        anchors.topMargin: 8
        anchors.right: timelineTabs.left
        anchors.rightMargin: 8
        spacing: 5
        height: 20

        StatusDot {
            anchors.verticalCenter: parent.verticalCenter
            active: controller.isActivityActive
            error: controller.isActivityError
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: controller.cleanLatestModel
            color: "#FFFFFF"
            font.family: "SF Pro Display"
            font.pixelSize: 10
            font.bold: true
            elide: Text.ElideRight
            width: parent.width - 24
        }
    }

    TimelineTabs {
        id: timelineTabs
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: topRow.verticalCenter
        currentTimeline: controller.timeline
        onTimelineSelected: function(key) {
            controller.setTimeline(key);
        }
    }

    // Row 2: Big Tokens & Cost / Reqs
    Text {
        id: bigTokens
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.top: parent.top
        anchors.topMargin: 29
        text: controller.totalTokensStr + " Tokens"
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 14
        font.bold: true
    }

    Text {
        id: costAndReqs
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: bigTokens.verticalCenter
        color: controller.flyingDeltaText !== "" ? "#30D158" : "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 11
        font.bold: true
        text: controller.flyingDeltaText !== "" ? controller.flyingDeltaText : (controller.costStr + "  |  " + controller.requestsStr + " reqs")
    }

    // Row 3: Live Ticker & 'Full' hint
    Text {
        id: tickerLabel
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        anchors.right: expandHint.left
        anchors.rightMargin: 8
        text: controller.tickerText
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        elide: Text.ElideRight
    }

    Text {
        id: expandHint
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: tickerLabel.verticalCenter
        text: "Full"
        color: "#8E8E93"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
    }
}
