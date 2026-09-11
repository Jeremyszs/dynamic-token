import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.15

Item {
    id: root
    width: island.width
    height: island.height

    property string currentView: backend ? backend.currentView : "min"
    property string timeline: backend ? backend.timeline : "today"

    // Target View Dimensions
    readonly property var viewSizes: {
        "min": { w: 320, h: 42, r: 21 },
        "normal": { w: 520, h: 136, r: 26 },
        "detailed": { w: 620, h: 430, r: 28 }
    }

    readonly property real targetW: viewSizes[currentView].w
    readonly property real targetH: viewSizes[currentView].h
    readonly property real targetR: viewSizes[currentView].r

    // Apple Dynamic Island Capsule Container
    Rectangle {
        id: island
        width: targetW
        height: targetH
        radius: targetR
        color: "#000000"
        border.color: mouseArea.containsMouse ? "#555558" : "#2C2C2E"
        border.width: 1

        // Hardware-Accelerated 165Hz GPU Animation via Qt Quick Scene Graph
        Behavior on width {
            SpringAnimation {
                spring: 3.8
                damping: 0.35
                epsilon: 0.25
            }
        }
        Behavior on height {
            SpringAnimation {
                spring: 3.8
                damping: 0.35
                epsilon: 0.25
            }
        }
        Behavior on radius {
            SpringAnimation {
                spring: 3.8
                damping: 0.35
                epsilon: 0.25
            }
        }
        Behavior on border.color {
            ColorAnimation { duration: 180 }
        }

        // Window dragging & clicking
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton

            property point clickPos: "0,0"
            property bool wasDragged: false

            onPressed: function(mouse) {
                clickPos = Qt.point(mouse.x, mouse.y)
                wasDragged = false
                backend.startDrag(mouse.x, mouse.y)
            }

            onPositionChanged: function(mouse) {
                if (pressed && mouse.buttons & Qt.LeftButton) {
                    var dx = mouse.x - clickPos.x
                    var dy = mouse.y - clickPos.y
                    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                        wasDragged = true
                        backend.dragWindow(mouse.x, mouse.y)
                    }
                }
            }

            onReleased: function(mouse) {
                if (wasDragged) {
                    backend.savePosition()
                    return
                }
                if (mouse.button === Qt.RightButton) {
                    backend.toggleDetailed()
                } else if (mouse.button === Qt.LeftButton) {
                    // Check if clicked interactive child
                    backend.cycleView()
                }
            }
        }

        // --- CONTENT LAYER ---
        Item {
            anchors.fill: parent

            // 1. MIN VIEW
            Item {
                id: minView
                anchors.fill: parent
                visible: currentView === "min"
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 150 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 8

                    // Breathing Green Dot
                    Rectangle {
                        id: minDot
                        width: 9
                        height: 9
                        radius: 4.5
                        color: "#30D158"
                        Layout.alignment: Qt.AlignVCenter

                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            running: true
                            NumberAnimation { from: 0.5; to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
                            NumberAnimation { from: 1.0; to: 0.5; duration: 1200; easing.type: Easing.InOutSine }
                        }
                    }

                    Text {
                        text: backend ? backend.shortModel : "--"
                        color: "#98989D"
                        font.family: "SF Pro Display"
                        font.pixelSize: 13
                        font.bold: true
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: backend ? (backend.totalTokensStr + " tok • " + backend.costStr) : "0 tok • $0.00"
                        color: "#FFFFFF"
                        font.family: "SF Pro Display"
                        font.pixelSize: 13
                        font.bold: true
                        Layout.alignment: Qt.AlignVCenter
                    }
                }
            }

            // 2. NORMAL VIEW
            Item {
                id: normView
                anchors.fill: parent
                visible: currentView === "normal"
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 180 } }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 6

                    // Top Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            width: 9
                            height: 9
                            radius: 4.5
                            color: "#30D158"
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Text {
                            text: backend ? backend.latestModel : "--"
                            color: "#FFFFFF"
                            font.family: "SF Pro Display"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        Item { Layout.fillWidth: true }

                        // Timeline Tabs
                        Row {
                            spacing: 4
                            Repeater {
                                model: ["Today", "7D", "30D", "All"]
                                Rectangle {
                                    width: 46
                                    height: 22
                                    radius: 11
                                    color: (backend && backend.timeline.toLowerCase() === modelData.toLowerCase()) ? "#2C2C2E" : "#141416"
                                    border.color: (backend && backend.timeline.toLowerCase() === modelData.toLowerCase()) ? "#555" : "#2C2C2E"
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData
                                        color: (backend && backend.timeline.toLowerCase() === modelData.toLowerCase()) ? "#FFF" : "#8E8E93"
                                        font.family: "SF Pro Display"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: backend.setTimeline(modelData.toLowerCase())
                                    }
                                }
                            }
                        }
                    }

                    // Metrics Row
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: backend ? (backend.totalTokensStr + " Tokens") : "0 Tokens"
                            color: "#FFFFFF"
                            font.family: "SF Pro Display"
                            font.pixelSize: 24
                            font.bold: true
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: backend ? (backend.costStr + " | " + backend.requestsStr + " reqs") : "$0.00 | 0 reqs"
                            color: "#0A84FF"
                            font.family: "SF Pro Display"
                            font.pixelSize: 14
                            font.bold: true
                        }
                    }

                    // Ticker Footer
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: backend ? backend.tickerText : "Listening for API calls..."
                            color: "#8E8E93"
                            font.family: "SF Pro Display"
                            font.pixelSize: 11
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "▾ Full"
                            color: "#636366"
                            font.family: "SF Pro Display"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }
                }
            }

            // 3. DETAILED VIEW
            Item {
                id: detView
                anchors.fill: parent
                visible: currentView === "detailed"
                opacity: visible ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 180 } }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12

                    // Header Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            width: 10
                            height: 10
                            radius: 5
                            color: "#30D158"
                        }

                        Text {
                            text: "Dynamic Island • 9router Token HUD"
                            color: "#FFFFFF"
                            font.family: "SF Pro Display"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        Item { Layout.fillWidth: true }

                        // Minimize & Shutdown Circular Buttons
                        Rectangle {
                            width: 26
                            height: 26
                            radius: 13
                            color: "#1C1C1E"
                            border.color: "#2C2C2E"
                            Text { anchors.centerIn: parent; text: "—"; color: "#FFF"; font.bold: true }
                            MouseArea { anchors.fill: parent; onClicked: backend.setView("min") }
                        }

                        Rectangle {
                            width: 26
                            height: 26
                            radius: 13
                            color: "#2A1214"
                            border.color: "#5A1E22"
                            Text { anchors.centerIn: parent; text: "✕"; color: "#FF453A"; font.bold: true }
                            MouseArea { anchors.fill: parent; onClicked: backend.shutdown() }
                        }
                    }

                    // Timeline Tabs Row
                    Row {
                        spacing: 6
                        Repeater {
                            model: ["Today", "7D", "30D", "All"]
                            Rectangle {
                                width: 52
                                height: 24
                                radius: 12
                                color: (backend && backend.timeline.toLowerCase() === modelData.toLowerCase()) ? "#2C2C2E" : "#141416"
                                border.color: (backend && backend.timeline.toLowerCase() === modelData.toLowerCase()) ? "#555" : "#2C2C2E"
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: (backend && backend.timeline.toLowerCase() === modelData.toLowerCase()) ? "#FFF" : "#8E8E93"
                                    font.family: "SF Pro Display"
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: backend.setTimeline(modelData.toLowerCase())
                                }
                            }
                        }
                    }

                    // 4-Column Stat Cards with Smooth 18px Radius
                    Rectangle {
                        Layout.fillWidth: true
                        height: 72
                        radius: 18
                        color: "#151517"
                        border.color: "#2C2C2E"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14

                            // Col 1
                            Column {
                                Layout.fillWidth: true
                                Text { text: "TOTAL TOKENS"; color: "#636366"; font.pixelSize: 9; font.bold: true; font.family: "SF Pro Display" }
                                Text { text: backend ? backend.totalTokensStr : "0"; color: "#FFFFFF"; font.pixelSize: 18; font.bold: true; font.family: "SF Pro Display" }
                            }
                            // Col 2
                            Column {
                                Layout.fillWidth: true
                                Text { text: "BURN COST"; color: "#636366"; font.pixelSize: 9; font.bold: true; font.family: "SF Pro Display" }
                                Text { text: backend ? backend.costStr : "$0.00"; color: "#30D158"; font.pixelSize: 18; font.bold: true; font.family: "SF Pro Display" }
                            }
                            // Col 3
                            Column {
                                Layout.fillWidth: true
                                Text { text: "REQUESTS"; color: "#636366"; font.pixelSize: 9; font.bold: true; font.family: "SF Pro Display" }
                                Text { text: backend ? backend.requestsStr : "0"; color: "#0A84FF"; font.pixelSize: 18; font.bold: true; font.family: "SF Pro Display" }
                            }
                            // Col 4
                            Column {
                                Layout.fillWidth: true
                                Text { text: "CACHE RATIO"; color: "#636366"; font.pixelSize: 9; font.bold: true; font.family: "SF Pro Display" }
                                Text { text: backend ? backend.cacheRatioStr : "0.0%"; color: "#FF9F0A"; font.pixelSize: 18; font.bold: true; font.family: "SF Pro Display" }
                            }
                        }
                    }

                    // Top Models Section
                    Text {
                        text: "TOP MODELS BREAKDOWN"
                        color: "#636366"
                        font.pixelSize: 11
                        font.bold: true
                        font.family: "SF Pro Display"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: backend ? backend.modelsModel : []
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: modelData.name; color: "#FFFFFF"; font.pixelSize: 12; font.bold: true; font.family: "SF Pro Display" }
                                    Item { Layout.fillWidth: true }
                                    Text { text: modelData.usage; color: "#8E8E93"; font.pixelSize: 12; font.family: "SF Pro Display" }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 5
                                    radius: 2.5
                                    color: "#1C1C1E"
                                    Rectangle {
                                        width: parent.width * Math.min(1.0, modelData.ratio)
                                        height: parent.height
                                        radius: 2.5
                                        color: "#0A84FF"
                                    }
                                }
                            }
                        }
                    }

                    // Live API History Section
                    Text {
                        text: "LIVE API CALL HISTORY"
                        color: "#636366"
                        font.pixelSize: 11
                        font.bold: true
                        font.family: "SF Pro Display"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Repeater {
                            model: backend ? backend.historyModel : []
                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle {
                                    width: 44
                                    height: 18
                                    radius: 6
                                    color: modelData.status === "ok" ? "#103E1D" : "#3D1214"
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.status === "ok" ? "200 OK" : "ERR"
                                        color: modelData.status === "ok" ? "#30D158" : "#FF453A"
                                        font.pixelSize: 9
                                        font.bold: true
                                        font.family: "SF Pro Display"
                                    }
                                }
                                Text { text: modelData.model; color: "#FFFFFF"; font.pixelSize: 12; font.family: "SF Pro Display" }
                                Item { Layout.fillWidth: true }
                                Text { text: "+" + modelData.tokens + " tok • " + modelData.time; color: "#8E8E93"; font.pixelSize: 11; font.family: "SF Pro Display" }
                            }
                        }
                    }
                }
            }
        }
    }
}
