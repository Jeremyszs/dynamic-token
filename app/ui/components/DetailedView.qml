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

    // 3. DEDICATED SECTION: ACCOUNT MANAGER (poolHeaderY = dp(154), h = dp(120))
    readonly property int poolHeaderY: root.dp(154)

    Text {
        x: root.dp(24)
        y: root.poolHeaderY - (implicitHeight / 2)
        text: "ACCOUNT MANAGER"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pointSize: 9
        font.bold: true
    }

    PillButton {
        x: root.dp(182)
        y: root.poolHeaderY - root.dp(10)
        width: root.dp(74)
        height: root.dp(20)
        buttonRadius: root.dp(8)
        text: "Refresh"
        normalColor: "#1C1C1F"
        textColor: "#A1A1A6"
        borderColor: "#333338"
        onClicked: controller.triggerRefresh()
    }

    // Provider Carousel & Action buttons
    readonly property string provLabel: controller.currentProvider.clean_name + " (" + (controller.selectedProviderIndex + 1) + "/" + controller.providersList.length + ")"
    readonly property int provLblLen: root.dp(provLabel.length * 6 + 18)

    CircleButton {
        x: root.width - root.dp(24) - root.dp(12) - root.dp(10)
        y: root.poolHeaderY - root.dp(10)
        radiusSize: root.dp(10)
        iconType: "right"
        onClicked: controller.nextProvider()
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: root.dp(24 + 32)
        y: root.poolHeaderY - (implicitHeight / 2)
        text: root.provLabel
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pointSize: 8
        font.bold: true
    }

    CircleButton {
        anchors.right: parent.right
        anchors.rightMargin: root.dp(24 + 32) + root.provLblLen
        y: root.poolHeaderY - root.dp(10)
        radiusSize: root.dp(10)
        iconType: "left"
        onClicked: controller.prevProvider()
    }

    PillButton {
        anchors.right: parent.right
        anchors.rightMargin: root.dp(24 + 32) + root.provLblLen + root.dp(14)
        y: root.poolHeaderY - root.dp(10)
        width: root.dp(72)
        height: root.dp(20)
        buttonRadius: root.dp(8)
        text: (controller.currentProvider.active_count > 0) ? "Disable All" : "Enable All"
        textColor: (controller.currentProvider.active_count > 0) ? "#A1A1A6" : "#30D158"
        normalColor: "#1C1C1F"
        borderColor: "#333338"
        onClicked: {
            controller.toggleProviderActive(
                controller.currentProvider.raw_name,
                controller.currentProvider.active_count > 0
            );
        }
    }

    // Account Manager Card Container (y = poolHeaderY + dp(14), h = dp(120))
    Rectangle {
        id: poolCard
        x: root.boxX1
        y: root.poolHeaderY + root.dp(14)
        width: root.boxW
        height: root.dp(120)
        radius: root.dp(16)
        color: "#121214"
        border.color: "#262629"
        border.width: 1

        readonly property int chainW: root.dp(210)
        readonly property int chainXStart: root.boxW - chainW
        readonly property int maxLeftW: chainXStart - root.dp(16) - root.dp(14)

        // Right Column: SELECT ACCOUNT
        Text {
            x: poolCard.chainXStart
            y: root.dp(16) - (implicitHeight / 2)
            text: "SELECT ACCOUNT"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pointSize: 7
            font.bold: true
        }

        // Account slots 1..8
        Row {
            x: poolCard.chainXStart
            y: root.dp(30)
            spacing: root.dp(4)

            Repeater {
                model: (controller.currentProvider.accounts || []).slice(0, 8)
                Rectangle {
                    id: slotBtn
                    required property var modelData
                    required property int index
                    width: root.dp(22)
                    height: root.dp(22)
                    radius: root.dp(6)
                    color: {
                        if (slotBtn.modelData.is_current) return "#1C3A24";
                        if (slotBtn.modelData.is_active) return "#232326";
                        return "#141416";
                    }
                    border.color: {
                        if (controller.currentAccount.slot_index === slotBtn.index) return "#FFFFFF";
                        if (slotBtn.modelData.is_current) return "#30D158";
                        if (slotBtn.modelData.is_active) return "#3C3C40";
                        return "#242426";
                    }
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: slotBtn.modelData.priority || (slotBtn.index + 1)
                        color: slotBtn.modelData.is_current ? "#30D158" : (slotBtn.modelData.is_active ? "#FFFFFF" : "#58585E")
                        font.family: "SF Pro Display"
                        font.pointSize: 8
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: controller.selectAccountSlot(controller.currentProvider.raw_name, slotBtn.index)
                    }
                }
            }
        }

        // Left Column:
        // Line 1: Email text & Status Badge
        Text {
            x: root.dp(16)
            y: root.dp(16) - (implicitHeight / 2)
            text: controller.currentAccount.full_email || "No accounts registered"
            color: "#FFFFFF"
            font.family: "SF Pro Display"
            font.pointSize: 10
            font.bold: true
            elide: Text.ElideRight
            width: poolCard.maxLeftW - statusBadge.width - root.dp(12)
        }

        Rectangle {
            id: statusBadge
            x: root.dp(16) + poolCard.maxLeftW - width
            y: root.dp(6)
            width: statusBadgeText.implicitWidth + root.dp(14)
            height: root.dp(18)
            radius: root.dp(6)
            color: controller.currentAccount.is_current ? "#0B2915" : (controller.currentAccount.is_active ? "#1A1A1D" : "#241416")
            border.color: controller.currentAccount.is_current ? "#144D26" : (controller.currentAccount.is_active ? "#333336" : "#4A1E22")
            border.width: 1

            Text {
                id: statusBadgeText
                anchors.centerIn: parent
                text: "P" + (controller.currentAccount.priority || 1) + " • " + (controller.currentAccount.is_current ? "Active Route" : (controller.currentAccount.is_active ? "Standby Ready" : "Disabled"))
                color: controller.currentAccount.is_current ? "#30D158" : (controller.currentAccount.is_active ? "#FFFFFF" : "#58585E")
                font.family: "SF Pro Display"
                font.pointSize: 7
                font.bold: true
            }
        }

        // Line 2: Quota Label on left, figures on right
        Text {
            x: root.dp(16)
            y: root.dp(38) - (implicitHeight / 2)
            text: controller.currentAccount.reset_time_left ? ("QUOTA  •  " + controller.currentAccount.reset_time_left) : "CURRENT QUOTA"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pointSize: 7
            font.bold: true
        }

        Text {
            x: root.dp(16) + poolCard.maxLeftW - implicitWidth
            y: root.dp(38) - (implicitHeight / 2)
            text: (controller.currentAccount.used_str || "0") + " / " + (controller.currentAccount.limit_str || "0") + " (" + (controller.currentAccount.used_pct_str || "0.0%") + ")"
            color: (controller.currentAccount.used_pct >= 90) ? "#FF453A" : ((controller.currentAccount.used_pct >= 75) ? "#FF9F0A" : "#FFFFFF")
            font.family: "SF Pro Display"
            font.pointSize: 8
            font.bold: true
        }

        // Line 3: Progress Bar
        Rectangle {
            x: root.dp(16)
            y: root.dp(49)
            width: poolCard.maxLeftW
            height: root.dp(6)
            radius: root.dp(3)
            color: "#202024"
            border.color: "#28282C"
            border.width: 1

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: Math.max(0, Math.min(parent.width, parent.width * ((controller.currentAccount.used_pct || 0) / 100.0)))
                radius: root.dp(3)
                color: (controller.currentAccount.used_pct >= 90) ? "#FF453A" : ((controller.currentAccount.used_pct >= 75) ? "#FF9F0A" : "#30D158")

                Behavior on width {
                    NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
                }
            }
        }

        // Line 4: Burn stats (Synchronized with timeline filter: Today / 7D / 30D / All-Time)
        Text {
            x: root.dp(16)
            y: root.dp(70) - (implicitHeight / 2)
            text: (controller.timeline === 'today' ? "Today" : (controller.timeline === '7d' ? "7D" : (controller.timeline === '30d' ? "30D" : "All-Time"))) + " Burn: " + (controller.currentAccount.timeline_burn_str || "0") + " tokens • " + (controller.currentAccount.timeline_reqs_str || "0") + " requests"
            color: "#A1A1A6"
            font.family: "SF Pro Display"
            font.pointSize: 8
        }

        // Line 5: Action Button & Provider Total summary
        PillButton {
            x: root.dp(16)
            y: root.dp(90)
            width: root.dp(124)
            height: root.dp(20)
            buttonRadius: root.dp(9)
            text: controller.currentAccount.is_active ? "Deactivate Account" : "Activate Account"
            textColor: controller.currentAccount.is_active ? "#FF6961" : "#30D158"
            normalColor: controller.currentAccount.is_active ? "#381618" : "#122E1A"
            borderColor: controller.currentAccount.is_active ? "#662228" : "#1E5E2A"
            onClicked: {
                if (controller.currentAccount.id) {
                    controller.toggleAccountActive(controller.currentAccount.id, controller.currentAccount.is_active);
                }
            }
        }

        Text {
            x: root.dp(16 + 124 + 14)
            y: root.dp(100) - (implicitHeight / 2)
            text: "Provider: " + (controller.currentProvider.active_count || 0) + "/" + (controller.currentProvider.total_count || 0) + " Active • " + controller.totalTokensStr + " tok"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pointSize: 8
        }
    }

    // 4. TOP MODELS BREAKDOWN (modelsHeaderY = dp(304))
    readonly property int modelsHeaderY: root.dp(304)

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

    // 5. LIVE API CALL HISTORY (feedHeaderY = dp(430))
    readonly property int feedHeaderY: root.dp(430)

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
