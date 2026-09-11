import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // Row 1: Status Dot, Model Name, Timeline Tabs
    Row {
        id: topRow
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.top: parent.top
        anchors.topMargin: 12
        anchors.right: timelineTabs.left
        anchors.rightMargin: 10
        spacing: 6
        height: 22

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
            width: parent.width - 26
        }
    }

    TimelineTabs {
        id: timelineTabs
        anchors.right: parent.right
        anchors.rightMargin: 16
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
        anchors.leftMargin: 16
        anchors.top: parent.top
        anchors.topMargin: 46
        text: controller.totalTokensStr + " Tokens"
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 15
        font.bold: true
    }

    Text {
        id: costAndReqs
        anchors.right: parent.right
        anchors.rightMargin: 16
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
        anchors.leftMargin: 16
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        anchors.right: expandHint.left
        anchors.rightMargin: 10
        text: controller.tickerText
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        elide: Text.ElideRight
    }

    Text {
        id: expandHint
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: tickerLabel.verticalCenter
        text: "Full"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
    }
}
