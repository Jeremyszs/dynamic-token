import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // Row 1: Status Dot, Model Name, Timeline Tabs
    StatusDot {
        id: statusDot
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.top: parent.top
        anchors.topMargin: 16
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    Text {
        id: modelTitle
        anchors.left: statusDot.right
        anchors.leftMargin: 8
        anchors.verticalCenter: statusDot.verticalCenter
        anchors.right: timelineTabs.left
        anchors.rightMargin: 12
        text: controller.cleanLatestModel
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 10
        font.bold: true
        elide: Text.ElideRight
    }

    TimelineTabs {
        id: timelineTabs
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: statusDot.verticalCenter
        currentTimeline: controller.timeline
        onTimelineSelected: function(key) {
            controller.setTimeline(key);
        }
    }

    // Row 2: Big Tokens & Cost / Reqs
    Text {
        id: bigTokens
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.top: parent.top
        anchors.topMargin: 52
        text: controller.totalTokensStr + " Tokens"
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 16
        font.bold: true
    }

    Text {
        id: costAndReqs
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: bigTokens.verticalCenter
        color: controller.flyingDeltaText !== "" ? "#30D158" : "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 12
        font.bold: true
        text: controller.flyingDeltaText !== "" ? controller.flyingDeltaText : (controller.costStr + "  |  " + controller.requestsStr + " reqs")
    }

    // Row 3: Live Ticker & 'Full' hint
    Text {
        id: tickerLabel
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 16
        anchors.right: expandHint.left
        anchors.rightMargin: 12
        text: controller.tickerText
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        elide: Text.ElideRight
    }

    Text {
        id: expandHint
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: tickerLabel.verticalCenter
        text: "Full"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
    }
}
