import QtQuick
import QtQuick.Layouts
import "."

Item {
    id: root
    anchors.fill: parent

    // 1. Header (y=16)
    Row {
        id: headerRow
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.top: parent.top
        anchors.topMargin: 12
        spacing: 6
        height: 22

        StatusDot {
            anchors.verticalCenter: parent.verticalCenter
            active: controller.isActivityActive
            error: controller.isActivityError
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "Token Usage & API Call History"
            color: "#FFFFFF"
            font.family: "SF Pro Display"
            font.pixelSize: 11
            font.bold: true
        }
    }

    // Header buttons (9R, minimize, close)
    Row {
        id: headerControls
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: headerRow.verticalCenter
        spacing: 6

        CircleButton {
            buttonText: "9R"
            normalColor: controller.is9routerRunning ? "#381C08" : "#281506"
            borderColor: controller.is9routerRunning ? "#8A420A" : "#542605"
            iconColor: "#FF9F0A"
            radiusSize: 11
            onClicked: controller.run9routerAction()
        }

        CircleButton {
            iconType: "minimize"
            normalColor: "#1C1C1E"
            borderColor: "#262629"
            iconColor: "#FFFFFF"
            radiusSize: 11
            onClicked: controller.setView("min")
        }

        CircleButton {
            iconType: "close"
            normalColor: "#241416"
            borderColor: "#4A1E22"
            iconColor: "#FF453A"
            radiusSize: 11
            onClicked: Qt.quit()
        }
    }

    // Row 2: Timeline Tabs on left & Latency telemetry on right
    Row {
        id: timelineRow
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.top: headerRow.bottom
        anchors.topMargin: 8
        height: 22

        TimelineTabs {
            currentTimeline: controller.timeline
            onTimelineSelected: function(key) {
                controller.setTimeline(key);
            }
        }
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: timelineRow.verticalCenter
        text: controller.latencySummaryStr
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 8
        font.bold: true
    }

    // 2. Primary Metrics Card
    Rectangle {
        id: statCard
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.top: timelineRow.bottom
        anchors.topMargin: 8
        height: 56
        radius: 12
        color: "#121214"
        border.color: "#262629"
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14

            Column {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "TOTAL TOKENS"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
                Text { text: controller.totalTokensStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
            }
            Column {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "BURN COST"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
                Text { text: controller.costStr; color: "#30D158"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
            }
            Column {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "REQUESTS"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
                Text { text: controller.requestsStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
            }
            Column {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "CACHE RATIO"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
                Text { text: controller.cacheRatioStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
            }
            Column {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "THINKING"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
                Text { text: controller.reasoningTokensStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
            }
        }
    }

    // 3. Section: Account Manager
    Item {
        id: accountManagerSection
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.top: statCard.bottom
        anchors.topMargin: 10
        height: 142

        // Section Header Row
        Item {
            id: amHeader
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 22

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "ACCOUNT MANAGER"
                    color: "#58585E"
                    font.family: "SF Pro Display"
                    font.pixelSize: 9
                    font.bold: true
                }

                PillButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Refresh"
                    normalColor: "#1C1C1F"
                    textColor: "#A1A1A6"
                    borderColor: "#333338"
                    buttonRadius: 7
                    onClicked: controller.triggerRefresh()
                }
            }

            // Right side: Carousel Navigation [‹] Provider (N/M) [›] + Disable/Enable All
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                PillButton {
                    anchors.verticalCenter: parent.verticalCenter
                    text: (controller.currentProvider.active_count > 0) ? "Disable All" : "Enable All"
                    textColor: (controller.currentProvider.active_count > 0) ? "#A1A1A6" : "#30D158"
                    normalColor: "#1C1C1F"
                    borderColor: "#333338"
                    buttonRadius: 7
                    onClicked: {
                        controller.toggleProviderActive(
                            controller.currentProvider.raw_name,
                            controller.currentProvider.active_count > 0
                        );
                    }
                }

        CircleButton {
            iconType: "left"
            radiusSize: 10
            onClicked: controller.prevProvider()
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: controller.currentProvider.clean_name + " (" + (controller.selectedProviderIndex + 1) + "/" + controller.providersList.length + ")"
            color: "#FFFFFF"
            font.family: "SF Pro Display"
            font.pixelSize: 9
            font.bold: true
        }

        CircleButton {
            iconType: "right"
            radiusSize: 10
            onClicked: controller.nextProvider()
        }
            }
        }

        // Account Manager Box Container
        Rectangle {
            id: amCard
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: amHeader.bottom
            anchors.topMargin: 6
            height: 114
            radius: 12
            color: "#121214"
            border.color: "#262629"
            border.width: 1

            // Left Column (Email, Quota Bar, Action Button)
            Item {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.top: parent.top
                anchors.topMargin: 10
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                anchors.right: slotSelectorArea.left
                anchors.rightMargin: 14

                // Line 1: Email & Status Badge
                Row {
                    id: emailRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 20

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: controller.currentAccount.full_email || "No accounts registered"
                        color: "#FFFFFF"
                        font.family: "SF Pro Display"
                        font.pixelSize: 11
                        font.bold: true
                        elide: Text.ElideRight
                        width: parent.width - statusPill.width - 10
                    }

                    Rectangle {
                        id: statusPill
                        anchors.verticalCenter: parent.verticalCenter
                        width: statusText.implicitWidth + 14
                        height: 20
                        radius: 6
                        color: controller.currentAccount.is_current ? "#0B2915" : (controller.currentAccount.is_active ? "#1A1A1D" : "#241416")
                        border.color: controller.currentAccount.is_current ? "#144D26" : (controller.currentAccount.is_active ? "#333336" : "#4A1E22")
                        border.width: 1

                        Text {
                            id: statusText
                            anchors.centerIn: parent
                            text: "P" + (controller.currentAccount.priority || 1) + " • " + (controller.currentAccount.is_current ? "Active Route" : (controller.currentAccount.is_active ? "Standby Ready" : "Disabled"))
                            color: controller.currentAccount.is_current ? "#30D158" : (controller.currentAccount.is_active ? "#FFFFFF" : "#58585E")
                            font.family: "SF Pro Display"
                            font.pixelSize: 8
                            font.bold: true
                        }
                    }
                }

                // Line 2: Quota Label & Countdown
                Item {
                    id: quotaLabelRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: emailRow.bottom
                    anchors.topMargin: 5
                    height: 14

                    Text {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: controller.currentAccount.reset_time_left ? ("QUOTA  •  " + controller.currentAccount.reset_time_left) : "CURRENT QUOTA"
                        color: "#58585E"
                        font.family: "SF Pro Display"
                        font.pixelSize: 8
                        font.bold: true
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: (controller.currentAccount.used_str || "0") + " / " + (controller.currentAccount.limit_str || "0") + " (" + (controller.currentAccount.used_pct_str || "0.0%") + ")"
                        color: (controller.currentAccount.used_pct >= 90) ? "#FF453A" : ((controller.currentAccount.used_pct >= 75) ? "#FF9F0A" : "#FFFFFF")
                        font.family: "SF Pro Display"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }

                // Line 3: Progress Bar
                Rectangle {
                    id: quotaTrack
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: quotaLabelRow.bottom
                    anchors.topMargin: 4
                    height: 6
                    radius: 3
                    color: "#202024"
                    border.color: "#28282C"
                    border.width: 1

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: Math.max(0, Math.min(parent.width, parent.width * ((controller.currentAccount.used_pct || 0) / 100.0)))
                        radius: 3
                        color: (controller.currentAccount.used_pct >= 90) ? "#FF453A" : ((controller.currentAccount.used_pct >= 75) ? "#FF9F0A" : "#30D158")

                        Behavior on width {
                            NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
                        }
                    }
                }

                // Line 4: Burn stats & Action Button
                Item {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 20

                    PillButton {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: controller.currentAccount.is_active ? "Deactivate Account" : "Activate Account"
                        textColor: controller.currentAccount.is_active ? "#FF6961" : "#30D158"
                        normalColor: controller.currentAccount.is_active ? "#381618" : "#122E1A"
                        borderColor: controller.currentAccount.is_active ? "#662228" : "#1E5E2A"
                        buttonRadius: 7
                        onClicked: {
                            if (controller.currentAccount.id) {
                                controller.toggleAccountActive(controller.currentAccount.id, controller.currentAccount.is_active);
                            }
                        }
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Provider: " + (controller.currentProvider.active_count || 0) + "/" + (controller.currentProvider.total_count || 0) + " Active"
                        color: "#58585E"
                        font.family: "SF Pro Display"
                        font.pixelSize: 8
                    }
                }
            }

            // Right Column: Account Slot Switcher (1..8)
            Item {
                id: slotSelectorArea
                anchors.right: parent.right
                anchors.rightMargin: 14
                anchors.top: parent.top
                anchors.topMargin: 10
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                width: 190

                Text {
                    id: slotTitle
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "SELECT ACCOUNT"
                    color: "#58585E"
                    font.family: "SF Pro Display"
                    font.pixelSize: 7
                    font.bold: true
                }

                Row {
                    anchors.left: parent.left
                    anchors.top: slotTitle.bottom
                    anchors.topMargin: 6
                    spacing: 4

                    Repeater {
                        model: (controller.currentProvider.accounts || []).slice(0, 8)
                        Rectangle {
                            id: slotBtn
                            required property var modelData
                            required property int index
                            width: 20
                            height: 20
                            radius: 6
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
                                font.pixelSize: 8
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
            }
        }
    }

    // 4. Section: Top Models Breakdown
    Item {
        id: modelsSection
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.top: accountManagerSection.bottom
        anchors.topMargin: 8
        height: 104

        Text {
            id: modelsHeader
            anchors.left: parent.left
            anchors.top: parent.top
            text: "TOP MODELS BREAKDOWN"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pixelSize: 9
            font.bold: true
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: modelsHeader.bottom
            anchors.topMargin: 6
            spacing: 6

            Repeater {
                model: controller.topModelsList
                Item {
                    id: modelRowItem
                    required property var modelData
                    width: parent.width
                    height: 24

                    Item {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: 14

                        Text {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelRowItem.modelData.clean_name
                            color: "#FFFFFF"
                            font.family: "SF Pro Display"
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            width: parent.width - modelTokensText.implicitWidth - 16
                        }

                        Text {
                            id: modelTokensText
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelRowItem.modelData.tokens_str
                            color: "#A1A1A6"
                            font.family: "SF Pro Display"
                            font.pixelSize: 8
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 6
                        radius: 3
                        color: "#202024"
                        border.color: "#28282C"
                        border.width: 1

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: Math.max(0, Math.min(parent.width, parent.width * modelRowItem.modelData.ratio))
                            radius: 3
                            color: "#E5E5EA"
                        }
                    }
                }
            }
        }
    }

    // 5. Section: Live API Call History
    Item {
        id: historySection
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.top: modelsSection.bottom
        anchors.topMargin: 8
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10

        Text {
            id: historyHeader
            anchors.left: parent.left
            anchors.top: parent.top
            text: "LIVE API CALL HISTORY"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pixelSize: 9
            font.bold: true
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: historyHeader.bottom
            anchors.topMargin: 6
            spacing: 5

            Repeater {
                model: controller.recentCallsList
                Item {
                    id: historyRowItem
                    required property var modelData
                    width: parent.width
                    height: 18

                    Rectangle {
                        id: badgePill
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: 48
                        height: 16
                        radius: 5
                        color: historyRowItem.modelData.is_ok ? "#0B2915" : "#2D0E11"
                        border.color: historyRowItem.modelData.is_ok ? "#144D26" : "#59181D"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: historyRowItem.modelData.status
                            color: historyRowItem.modelData.is_ok ? "#30D158" : "#FF453A"
                            font.family: "SF Pro Display"
                            font.pixelSize: 7
                            font.bold: true
                        }
                    }

                    Text {
                        anchors.left: badgePill.right
                        anchors.leftMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: statsLabel.left
                        anchors.rightMargin: 8
                        text: historyRowItem.modelData.model
                        color: "#FFFFFF"
                        font.family: "SF Pro Display"
                        font.pixelSize: 9
                        elide: Text.ElideRight
                    }

                    Text {
                        id: statsLabel
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: historyRowItem.modelData.stats_str
                        color: "#A1A1A6"
                        font.family: "SF Pro Display"
                        font.pixelSize: 8
                    }
                }
            }
        }
    }
}
