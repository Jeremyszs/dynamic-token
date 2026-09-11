import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // Tkinter constants: box_x1 = 22, box_w = w - 44
    readonly property int boxX1: 22
    readonly property int boxW: width - 44

    // 1. Header (y=24)
    // place_dot(24, 24)
    StatusDot {
        id: statusDot
        x: 14
        y: 14
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // create_text(44, 24, anchor='w', text='Token Usage & API Call History', font=(FONT_NAME, 11, 'bold'))
    Text {
        x: 44
        y: 24 - (implicitHeight / 2)
        text: "Token Usage & API Call History"
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 11
        font.bold: true
    }

    // Header Controls at y=24: 9R at w - 92, minimize at w - 62, close at w - 32
    CircleButton {
        x: root.width - 92 - 12
        y: 24 - 12
        buttonText: "9R"
        normalColor: controller.is9routerRunning ? "#381C08" : "#281506"
        borderColor: controller.is9routerRunning ? "#8A420A" : "#542605"
        iconColor: "#FF9F0A"
        radiusSize: 12
        onClicked: controller.run9routerAction()
    }

    CircleButton {
        x: root.width - 62 - 12
        y: 24 - 12
        iconType: "minimize"
        normalColor: "#1C1C1E"
        borderColor: "#262629"
        iconColor: "#FFFFFF"
        radiusSize: 12
        onClicked: controller.setView("min")
    }

    CircleButton {
        x: root.width - 32 - 12
        y: 24 - 12
        iconType: "close"
        normalColor: "#241416"
        borderColor: "#4A1E22"
        iconColor: "#FF453A"
        radiusSize: 12
        onClicked: Qt.quit()
    }

    // Row 2 (y=54): Timeline Tabs & Latency Metric
    // render_timeline_tabs(24, 54, anchor='w')
    TimelineTabs {
        x: 24
        y: 54 - 10
        currentTimeline: controller.timeline
        onTimelineSelected: function(key) {
            controller.setTimeline(key);
        }
    }

    // create_text(w - 24, 54, anchor='e', text=lat_txt, font=(FONT_NAME, 8, 'bold'))
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 24
        y: 54 - (implicitHeight / 2)
        text: controller.latencySummaryStr
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 8
        font.bold: true
    }

    // 2. PRIMARY METRICS CARD (y=74, h=66, box_x1=22, box_w=w-44)
    Rectangle {
        id: statCard
        x: root.boxX1
        y: 74
        width: root.boxW
        height: 66
        radius: 16
        color: "#121214"
        border.color: "#262629"
        border.width: 1

        readonly property int colW: width / 5

        // Col 0: TOTAL TOKENS
        Item {
            x: 14; y: 0; width: statCard.colW; height: 66
            Text { y: 18 - (implicitHeight / 2); text: "TOTAL TOKENS"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
            Text { y: 44 - (implicitHeight / 2); text: controller.totalTokensStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
        }
        // Col 1: BURN COST
        Item {
            x: statCard.colW + 14; y: 0; width: statCard.colW; height: 66
            Text { y: 18 - (implicitHeight / 2); text: "BURN COST"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
            Text { y: 44 - (implicitHeight / 2); text: controller.costStr; color: "#30D158"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
        }
        // Col 2: REQUESTS
        Item {
            x: statCard.colW * 2 + 14; y: 0; width: statCard.colW; height: 66
            Text { y: 18 - (implicitHeight / 2); text: "REQUESTS"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
            Text { y: 44 - (implicitHeight / 2); text: controller.requestsStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
        }
        // Col 3: CACHE RATIO
        Item {
            x: statCard.colW * 3 + 14; y: 0; width: statCard.colW; height: 66
            Text { y: 18 - (implicitHeight / 2); text: "CACHE RATIO"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
            Text { y: 44 - (implicitHeight / 2); text: controller.cacheRatioStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
        }
        // Col 4: THINKING
        Item {
            x: statCard.colW * 4 + 14; y: 0; width: statCard.colW; height: 66
            Text { y: 18 - (implicitHeight / 2); text: "THINKING"; color: "#58585E"; font.family: "SF Pro Display"; font.pixelSize: 8; font.bold: true }
            Text { y: 44 - (implicitHeight / 2); text: controller.reasoningTokensStr; color: "#FFFFFF"; font.family: "SF Pro Display"; font.pixelSize: 13; font.bold: true }
        }
    }

    // 3. DEDICATED SECTION: ACCOUNT MANAGER (y=154, h=120)
    readonly property int poolHeaderY: 154

    // Title at (24, pool_header_y)
    Text {
        x: 24
        y: root.poolHeaderY - (implicitHeight / 2)
        text: "ACCOUNT MANAGER"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
    }

    // Refresh button at (x1=182, y1=pool_header_y - 10, x2=256, y2=pool_header_y + 10)
    PillButton {
        x: 182
        y: root.poolHeaderY - 10
        width: 74
        height: 20
        buttonRadius: 8
        text: "Refresh"
        normalColor: "#1C1C1F"
        textColor: "#A1A1A6"
        borderColor: "#333338"
        onClicked: controller.triggerRefresh()
    }

    // Provider Level Navigation & Disable All
    // In Tkinter: car_x = w - 24; [›] at car_x - 12; label at car_x - 32; [‹] at car_x - 32 - prov_lbl_len; Disable All at left
    readonly property string provLabel: controller.currentProvider.clean_name + " (" + (controller.selectedProviderIndex + 1) + "/" + controller.providersList.length + ")"
    readonly property int provLblLen: provLabel.length * 6 + 18

    CircleButton {
        x: root.width - 24 - 12 - 10
        y: root.poolHeaderY - 10
        radiusSize: 10
        iconType: "right"
        onClicked: controller.nextProvider()
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 24 + 32
        y: root.poolHeaderY - (implicitHeight / 2)
        text: root.provLabel
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 8
        font.bold: true
    }

    CircleButton {
        anchors.right: parent.right
        anchors.rightMargin: 24 + 32 + root.provLblLen
        y: root.poolHeaderY - 10
        radiusSize: 10
        iconType: "left"
        onClicked: controller.prevProvider()
    }

    PillButton {
        anchors.right: parent.right
        anchors.rightMargin: 24 + 32 + root.provLblLen + 14
        y: root.poolHeaderY - 10
        width: 72
        height: 20
        buttonRadius: 8
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

    // Account Manager Card Container (y = pool_header_y + 14 = 168, h = 120)
    Rectangle {
        id: poolCard
        x: root.boxX1
        y: root.poolHeaderY + 14
        width: root.boxW
        height: 120
        radius: 16
        color: "#121214"
        border.color: "#262629"
        border.width: 1

        readonly property int chainW: 210
        readonly property int chainXStart: root.boxW - chainW
        readonly property int maxLeftW: chainXStart - 16 - 14

        // Right Column: SELECT ACCOUNT at chain_x_start, pool_box_y + 16
        Text {
            x: poolCard.chainXStart
            y: 16 - (implicitHeight / 2)
            text: "SELECT ACCOUNT"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pixelSize: 7
            font.bold: true
        }

        // Account slots 1..8 at bx1 = slot_x (bx2=slot_x+22, by1=30, by2=52, dx=26)
        Row {
            x: poolCard.chainXStart
            y: 30
            spacing: 4

            Repeater {
                model: (controller.currentProvider.accounts || []).slice(0, 8)
                Rectangle {
                    id: slotBtn
                    required property var modelData
                    required property int index
                    width: 22
                    height: 22
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

        // Left Column:
        // Line 1 (y=16): Email text & Status Badge
        Text {
            x: 16
            y: 16 - (implicitHeight / 2)
            text: controller.currentAccount.full_email || "No accounts registered"
            color: "#FFFFFF"
            font.family: "SF Pro Display"
            font.pixelSize: 10
            font.bold: true
            elide: Text.ElideRight
            width: poolCard.maxLeftW - statusBadge.width - 12
        }

        Rectangle {
            id: statusBadge
            x: 16 + poolCard.maxLeftW - width
            y: 6
            width: statusBadgeText.implicitWidth + 14
            height: 18
            radius: 6
            color: controller.currentAccount.is_current ? "#0B2915" : (controller.currentAccount.is_active ? "#1A1A1D" : "#241416")
            border.color: controller.currentAccount.is_current ? "#144D26" : (controller.currentAccount.is_active ? "#333336" : "#4A1E22")
            border.width: 1

            Text {
                id: statusBadgeText
                anchors.centerIn: parent
                text: "P" + (controller.currentAccount.priority || 1) + " • " + (controller.currentAccount.is_current ? "Active Route" : (controller.currentAccount.is_active ? "Standby Ready" : "Disabled"))
                color: controller.currentAccount.is_current ? "#30D158" : (controller.currentAccount.is_active ? "#FFFFFF" : "#58585E")
                font.family: "SF Pro Display"
                font.pixelSize: 7
                font.bold: true
            }
        }

        // Line 2 (y=38): Current Quota Status (Label on left, figures on right)
        Text {
            x: 16
            y: 38 - (implicitHeight / 2)
            text: controller.currentAccount.reset_time_left ? ("QUOTA  •  " + controller.currentAccount.reset_time_left) : "CURRENT QUOTA"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pixelSize: 7
            font.bold: true
        }

        Text {
            x: 16 + poolCard.maxLeftW - implicitWidth
            y: 38 - (implicitHeight / 2)
            text: (controller.currentAccount.used_str || "0") + " / " + (controller.currentAccount.limit_str || "0") + " (" + (controller.currentAccount.used_pct_str || "0.0%") + ")"
            color: (controller.currentAccount.used_pct >= 90) ? "#FF453A" : ((controller.currentAccount.used_pct >= 75) ? "#FF9F0A" : "#FFFFFF")
            font.family: "SF Pro Display"
            font.pixelSize: 8
            font.bold: true
        }

        // Line 3 (y=49..55): Progress Bar
        Rectangle {
            x: 16
            y: 49
            width: poolCard.maxLeftW
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

        // Line 4 (y=70): Individual Account Token Used
        Text {
            x: 16
            y: 70 - (implicitHeight / 2)
            text: (controller.timeline === 'today' ? "Today" : (controller.timeline === '7d' ? "7D" : (controller.timeline === '30d' ? "30D" : "All-Time"))) + " Burn: " + (controller.currentAccount.used_str || "0") + " tokens • " + (controller.currentAccount.reqs || 0) + " requests"
            color: "#A1A1A6"
            font.family: "SF Pro Display"
            font.pixelSize: 8
        }

        // Line 5 (y=90..110): Action Button & Provider Total summary
        PillButton {
            x: 16
            y: 90
            width: 124
            height: 20
            buttonRadius: 9
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
            x: 16 + 124 + 14
            y: 100 - (implicitHeight / 2)
            text: "Provider: " + (controller.currentProvider.active_count || 0) + "/" + (controller.currentProvider.total_count || 0) + " Active • " + controller.totalTokensStr + " tok"
            color: "#58585E"
            font.family: "SF Pro Display"
            font.pixelSize: 8
        }
    }

    // 4. TOP MODELS BREAKDOWN (y = pool_box_y + pool_box_h + 16 = 168 + 120 + 16 = 304)
    readonly property int modelsHeaderY: 304

    Text {
        x: 24
        y: root.modelsHeaderY - (implicitHeight / 2)
        text: "TOP MODELS BREAKDOWN"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
    }

    // 3 Model rows at bar_y = models_header_y + 24 = 328, dy = 32
    Repeater {
        model: controller.topModelsList
        Item {
            id: modelRowItem
            required property var modelData
            required property int index

            readonly property int currentBarY: root.modelsHeaderY + 24 + (index * 32)
            x: 0
            y: currentBarY
            width: root.width
            height: 26

            Text {
                x: 24
                y: -(implicitHeight / 2)
                text: modelRowItem.modelData.clean_name
                color: "#FFFFFF"
                font.family: "SF Pro Display"
                font.pixelSize: 9
                elide: Text.ElideRight
                width: root.width - 48 - modelTokensStat.implicitWidth - 16
            }

            Text {
                id: modelTokensStat
                anchors.right: parent.right
                anchors.rightMargin: 24
                y: -(implicitHeight / 2)
                text: modelRowItem.modelData.tokens_str
                color: "#A1A1A6"
                font.family: "SF Pro Display"
                font.pixelSize: 8
            }

            Rectangle {
                x: 24
                y: 14
                width: root.width - 48
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

    // 5. LIVE API CALL HISTORY (feed_header_y = 328 + 3*32 + 6 = 430)
    readonly property int feedHeaderY: 430

    Text {
        x: 24
        y: root.feedHeaderY - (implicitHeight / 2)
        text: "LIVE API CALL HISTORY"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
    }

    // 3 Recent call rows at feed_y = feed_header_y + 20 = 450, dy = 22
    Repeater {
        model: controller.recentCallsList
        Item {
            id: historyRowItem
            required property var modelData
            required property int index

            readonly property int currentFeedY: root.feedHeaderY + 20 + (index * 22)
            x: 0
            y: currentFeedY
            width: root.width
            height: 20

            Rectangle {
                x: 24
                y: -2
                width: 52
                height: 18
                radius: 6
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
                x: 86
                y: 7 - (implicitHeight / 2)
                text: historyRowItem.modelData.model
                color: "#FFFFFF"
                font.family: "SF Pro Display"
                font.pixelSize: 9
                elide: Text.ElideRight
                width: root.width - 86 - feedStatsStat.implicitWidth - 16
            }

            Text {
                id: feedStatsStat
                anchors.right: parent.right
                anchors.rightMargin: 24
                y: 7 - (implicitHeight / 2)
                text: historyRowItem.modelData.stats_str
                color: "#A1A1A6"
                font.family: "SF Pro Display"
                font.pixelSize: 9
            }
        }
    }
}
