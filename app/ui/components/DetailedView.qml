import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    function dp(px) { return controller.scaler.dp(px); }

    readonly property int boxX1: root.dp(22)
    readonly property int boxW: width - (root.dp(22) * 2)

    // 1. Header (y = dp(24))
    StatusDot {
        id: statusDot
        x: root.dp(24) - (width / 2)
        y: root.dp(24) - (height / 2)
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    Text {
        x: root.dp(44)
        y: root.dp(24) - (implicitHeight / 2)
        text: "Token Usage & API Call History"
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pointSize: 11
        font.bold: true
    }

    // Header Controls at y = dp(24): 9R, minimize, close
    CircleButton {
        x: root.width - root.dp(92) - (width / 2)
        y: root.dp(24) - (height / 2)
        buttonText: "9R"
        normalColor: controller.is9routerRunning ? "#381C08" : "#281506"
        borderColor: controller.is9routerRunning ? "#8A420A" : "#542605"
        iconColor: "#FF9F0A"
        radiusSize: root.dp(12)
        onClicked: controller.run9routerAction()
    }

    CircleButton {
        x: root.width - root.dp(62) - (width / 2)
        y: root.dp(24) - (height / 2)
        iconType: "minimize"
        normalColor: "#1C1C1E"
        borderColor: "#262629"
        iconColor: "#FFFFFF"
        radiusSize: root.dp(12)
        onClicked: controller.setView("min")
    }

    CircleButton {
        x: root.width - root.dp(32) - (width / 2)
        y: root.dp(24) - (height / 2)
        iconType: "close"
        normalColor: "#241416"
        borderColor: "#4A1E22"
        iconColor: "#FF453A"
        radiusSize: root.dp(12)
        onClicked: Qt.quit()
    }

    // Row 2 (y = dp(54)): Timeline Tabs & Latency Metric
    TimelineTabs {
        x: root.dp(24)
        y: root.dp(54) - (height / 2)
        currentTimeline: controller.timeline
        onTimelineSelected: function(key) {
            controller.setTimeline(key);
        }
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: root.dp(24)
        y: root.dp(54) - (implicitHeight / 2)
        text: controller.latencySummaryStr
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pointSize: 8
        font.bold: true
    }

    // 2. PRIMARY METRICS CARD (y = dp(74), h = dp(66), boxX1 = dp(22), boxW = w - 2*dp(22))
    Rectangle {
        id: statCard
        x: root.boxX1
        y: root.dp(74)
        width: root.boxW
        height: root.dp(66)
        radius: root.dp(16)
        color: "#121214"
        border.color: "#262629"
        border.width: 1

        readonly property int colW: width / 5

        // Col 0: TOTAL TOKENS
        Item {
            x: root.dp(14); y: 0; width: statCard.colW; height: parent.height
            Text { y: root.dp(18) - (implicitHeight / 2); text: "TOTAL TOKENS"; color: "#58585E"; font.family: "SF Pro Display"; font.pointSize: 8; font.bold: true }
            Text { y: root.dp(44) - (implicitHeight / 2); text: controller.totalTokensStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pointSize: 13; font.bold: true }
        }
        // Col 1: BURN COST
        Item {
            x: statCard.colW + root.dp(14); y: 0; width: statCard.colW; height: parent.height
            Text { y: root.dp(18) - (implicitHeight / 2); text: "BURN COST"; color: "#58585E"; font.family: "SF Pro Display"; font.pointSize: 8; font.bold: true }
            Text { y: root.dp(44) - (implicitHeight / 2); text: controller.costStr; color: "#30D158"; font.family: "SF Pro Display"; font.pointSize: 13; font.bold: true }
        }
        // Col 2: REQUESTS
        Item {
            x: statCard.colW * 2 + root.dp(14); y: 0; width: statCard.colW; height: parent.height
            Text { y: root.dp(18) - (implicitHeight / 2); text: "REQUESTS"; color: "#58585E"; font.family: "SF Pro Display"; font.pointSize: 8; font.bold: true }
            Text { y: root.dp(44) - (implicitHeight / 2); text: controller.requestsStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pointSize: 13; font.bold: true }
        }
        // Col 3: CACHE RATIO
        Item {
            x: statCard.colW * 3 + root.dp(14); y: 0; width: statCard.colW; height: parent.height
            Text { y: root.dp(18) - (implicitHeight / 2); text: "CACHE RATIO"; color: "#58585E"; font.family: "SF Pro Display"; font.pointSize: 8; font.bold: true }
            Text { y: root.dp(44) - (implicitHeight / 2); text: controller.cacheRatioStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pointSize: 13; font.bold: true }
        }
        // Col 4: THINKING
        Item {
            x: statCard.colW * 4 + root.dp(14); y: 0; width: statCard.colW; height: parent.height
            Text { y: root.dp(18) - (implicitHeight / 2); text: "THINKING"; color: "#58585E"; font.family: "SF Pro Display"; font.pointSize: 8; font.bold: true }
            Text { y: root.dp(44) - (implicitHeight / 2); text: controller.reasoningTokensStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pointSize: 13; font.bold: true }
        }
    }

    // 3. TOP MODELS BREAKDOWN (modelsHeaderY = dp(154))
    readonly property int modelsHeaderY: root.dp(154)

    Text {
        x: root.dp(24)
        y: root.modelsHeaderY - (implicitHeight / 2)
        text: "TOP MODELS BREAKDOWN"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pointSize: 9
        font.bold: true
    }

    Repeater {
        model: controller.topModelsList
        Item {
            id: modelRowItem
            required property var modelData
            required property int index

            readonly property int currentBarY: root.modelsHeaderY + root.dp(24) + (index * root.dp(32))
            x: 0
            y: currentBarY
            width: root.width
            height: root.dp(26)

            Text {
                x: root.dp(24)
                y: -(implicitHeight / 2)
                text: modelRowItem.modelData.clean_name
                color: "#FFFFFF"
                font.family: "SF Pro Display"
                font.pointSize: 9
                elide: Text.ElideRight
                width: root.width - root.dp(48) - modelTokensStat.implicitWidth - root.dp(16)
            }

            Text {
                id: modelTokensStat
                anchors.right: parent.right
                anchors.rightMargin: root.dp(24)
                y: -(implicitHeight / 2)
                text: modelRowItem.modelData.tokens_str
                color: "#A1A1A6"
                font.family: "SF Pro Display"
                font.pointSize: 8
            }

            Rectangle {
                x: root.dp(24)
                y: root.dp(14)
                width: root.width - root.dp(48)
                height: root.dp(6)
                radius: root.dp(3)
                color: "#202024"
                border.color: "#28282C"
                border.width: 1

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: Math.max(0, Math.min(parent.width, parent.width * modelRowItem.modelData.ratio))
                    radius: root.dp(3)
                    color: "#E5E5EA"
                }
            }
        }
    }

    // 4. LIVE API CALL HISTORY (feedHeaderY = dp(280))
    readonly property int feedHeaderY: root.dp(280)

    Text {
        x: root.dp(24)
        y: root.feedHeaderY - (implicitHeight / 2)
        text: "LIVE API CALL HISTORY"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pointSize: 9
        font.bold: true
    }

    Repeater {
        model: controller.recentCallsList
        Item {
            id: historyRowItem
            required property var modelData
            required property int index

            readonly property int currentFeedY: root.feedHeaderY + root.dp(20) + (index * root.dp(22))
            x: 0
            y: currentFeedY
            width: root.width
            height: root.dp(20)

            Rectangle {
                x: root.dp(24)
                y: -root.dp(2)
                width: root.dp(52)
                height: root.dp(18)
                radius: root.dp(6)
                color: historyRowItem.modelData.is_ok ? "#0B2915" : "#2D0E11"
                border.color: historyRowItem.modelData.is_ok ? "#144D26" : "#59181D"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: historyRowItem.modelData.status
                    color: historyRowItem.modelData.is_ok ? "#30D158" : "#FF453A"
                    font.family: "SF Pro Display"
                    font.pointSize: 7
                    font.bold: true
                }
            }

            Text {
                x: root.dp(86)
                y: root.dp(7) - (implicitHeight / 2)
                text: historyRowItem.modelData.model
                color: "#FFFFFF"
                font.family: "SF Pro Display"
                font.pointSize: 9
                elide: Text.ElideRight
                width: root.width - root.dp(86) - feedStatsStat.implicitWidth - root.dp(16)
            }

            Text {
                id: feedStatsStat
                anchors.right: parent.right
                anchors.rightMargin: root.dp(24)
                y: root.dp(7) - (implicitHeight / 2)
                text: historyRowItem.modelData.stats_str
                color: "#A1A1A6"
                font.family: "SF Pro Display"
                font.pointSize: 9
            }
        }
    }
}
