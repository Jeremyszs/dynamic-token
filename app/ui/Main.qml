import QtQuick
import QtQuick.Window
import "components"

Window {
    id: window
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool

    width: controller.targetWidth
    height: controller.targetHeight
    x: controller.targetX
    y: controller.targetY

    Behavior on width {
        NumberAnimation {
            duration: 380
            easing.type: Easing.OutBack
            easing.overshoot: 1.06
        }
    }
    Behavior on height {
        NumberAnimation {
            duration: 380
            easing.type: Easing.OutBack
            easing.overshoot: 1.06
        }
    }

    // Dragging state
    property point dragStartPoint: Qt.point(0, 0)
    property bool isDragging: false
    property bool wasDragged: false

    // Root Container
    Item {
        id: rootContainer
        anchors.fill: parent

        // Main Island Capsule with Smooth Corners & Specular Glow
        IslandCapsule {
            id: mainCapsule
            anchors.fill: parent
            anchors.rightMargin: (controller.currentView === "min" && controller.isSplitActive) ? 56 : 0
            cornerRadius: controller.targetRadius
            isDockedNotch: controller.isDockedNotch
            isHovered: controller.isHovered
            isActivityActive: controller.isActivityActive
            isActivityError: controller.isActivityError

            Behavior on anchors.rightMargin {
                NumberAnimation { duration: 180; easing.type: Easing.OutBack }
            }
        }

        // Split Island Activity Bubble (ejected to the right when active generation occurs)
        Rectangle {
            id: splitBubble
            visible: controller.currentView === "min" && controller.isSplitActive
            width: 46
            height: parent.height
            radius: height / 2
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            color: "#000000"
            border.color: controller.isHovered ? "#444448" : "#262629"
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: controller.latestTps > 0 ? ("⚡ " + Math.round(controller.latestTps)) : "⚡"
                color: "#FF9F0A"
                font.family: "SF Pro Display"
                font.pixelSize: 9
                font.bold: true
            }

            Behavior on visible {
                NumberAnimation { duration: 150 }
            }
        }

        // Min View Content
        MinView {
            id: minView
            visible: controller ? (controller.currentView === "min") : true
            anchors.fill: parent
            anchors.rightMargin: (controller && controller.isSplitActive) ? 56 : 0
        }

        // Normal View Content
        NormalView {
            id: normalView
            visible: controller ? (controller.currentView === "normal") : false
            anchors.fill: parent
        }

        // Detailed View Content
        DetailedView {
            id: detailedView
            visible: controller ? (controller.currentView === "detailed") : false
            anchors.fill: parent
        }

        // Background Window Drag Area (Behind interactive child controls)
        MouseArea {
            id: windowDragArea
            anchors.fill: parent
            z: -1
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.ArrowCursor

            onEntered: {
                controller.isHovered = true;
            }
            onExited: {
                controller.isHovered = false;
            }

            onPressed: function(mouse) {
                if (mouse.button === Qt.LeftButton) {
                    window.dragStartPoint = Qt.point(mouse.x, mouse.y);
                    window.isDragging = false;
                    window.wasDragged = false;
                } else if (mouse.button === Qt.RightButton) {
                    controller.toggleDetailed();
                }
            }

            onPositionChanged: function(mouse) {
                if (mouse.buttons & Qt.LeftButton) {
                    var dx = mouse.x - window.dragStartPoint.x;
                    var dy = mouse.y - window.dragStartPoint.y;
                    if (Math.abs(dx) > 6 || Math.abs(dy) > 6) {
                        window.isDragging = true;
                        window.wasDragged = true;
                        window.x += dx;
                        window.y += dy;
                    }
                }
            }

            onReleased: function(mouse) {
                if (mouse.button === Qt.LeftButton) {
                    if (window.wasDragged) {
                        window.isDragging = false;
                        window.wasDragged = false;

                        // Check magnetic screen-top docking
                        var screenTop = window.screen.virtualY;
                        var distToTop = Math.abs(window.y - screenTop);
                        if (distToTop <= 16) {
                            window.y = screenTop;
                            controller.setDockedNotch(true);
                        } else {
                            controller.setDockedNotch(false);
                        }
                        controller.updateWindowPosition(window.x, window.y);
                    } else {
                        // Click on background cycles views
                        controller.cycleView();
                    }
                }
            }
        }
    }
}
