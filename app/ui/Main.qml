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

    Connections {
        target: controller
        function onViewChanged() {
            // Restore and enforce x and y bindings on view change
            window.x = controller.targetX;
            window.y = controller.targetY;
        }
    }

    onScreenChanged: {
        controller.updateScreenDpr(window.screen);
    }
    Component.onCompleted: {
        controller.updateScreenDpr(window.screen);
    }

    Behavior on width {
        NumberAnimation {
            duration: 250
            easing.type: Easing.OutQuad
        }
    }
    Behavior on height {
        NumberAnimation {
            duration: 250
            easing.type: Easing.OutQuad
        }
    }
    Behavior on x {
        id: xAnim
        enabled: !window.isDragging
        NumberAnimation {
            duration: 200
            easing.type: Easing.OutQuad
        }
    }
    Behavior on y {
        id: yAnim
        enabled: !window.isDragging
        NumberAnimation {
            duration: 200
            easing.type: Easing.OutQuad
        }
    }

    // Dragging state
    property point dragStartCursor: Qt.point(0, 0)
    property point dragStartWinPos: Qt.point(0, 0)
    property bool isDragging: false
    property bool wasDragged: false

    function endDragAndClamp() {
        if (window.wasDragged) {
            window.isDragging = false;
            window.wasDragged = false;
            var res = controller.clampGeometry(window.x, window.y, window.width, window.height);
            var targetX = res[0];
            var targetY = res[1];
            window.x = targetX;
            window.y = targetY;
        }
    }

    // Root Container
    Item {
        id: rootContainer
        anchors.fill: parent

        // Main Island Capsule with Smooth Corners & Specular Glow
        IslandCapsule {
            id: mainCapsule
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: (controller.currentView === "min" && controller.isSplitActive) ? splitBubble.left : parent.right
            anchors.rightMargin: (controller.currentView === "min" && controller.isSplitActive) ? 10 : 0
            cornerRadius: controller.targetRadius
            isDockedNotch: controller.isDockedNotch
            isHovered: controller.isHovered
            isActivityActive: controller.isActivityActive
            isActivityError: controller.isActivityError
        }

        // Split Island Activity Bubble (ejected to the right when active generation occurs)
        Item {
            id: splitBubble
            visible: controller.currentView === "min" && controller.isSplitActive
            width: Math.max(56, splitText.implicitWidth + 24)
            height: parent.height
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            IslandCapsule {
                anchors.fill: parent
                cornerRadius: parent.height / 2
                isDockedNotch: controller.isDockedNotch
                isHovered: controller.isHovered
                isActivityActive: false
                isActivityError: false
            }

            Text {
                id: splitText
                anchors.centerIn: parent
                text: {
                    var tps = controller.latestTps;
                    if (!tps || tps <= 0) return "";
                    return Math.round(tps) + " t/s";
                }
                color: "#FF9F0A"
                font.family: "SF Pro Display"
                font.pointSize: 9
                font.bold: true
            }

            Behavior on visible {
                NumberAnimation { duration: 150 }
            }
        }

        // Min View Content
        MinView {
            id: minView
            objectName: "minView"
            visible: controller ? (controller.currentView === "min") : true
            enabled: visible
            opacity: visible ? 1.0 : 0.0
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: mainCapsule.width
            clip: true
        }

        // Normal View Content
        NormalView {
            id: normalView
            visible: controller ? (controller.currentView === "normal") : false
            enabled: visible
            opacity: visible ? 1.0 : 0.0
            anchors.fill: parent
            clip: true
        }

        // Detailed View Content
        DetailedView {
            id: detailedView
            visible: controller ? (controller.currentView === "detailed") : false
            enabled: visible
            opacity: visible ? 1.0 : 0.0
            anchors.fill: parent
            clip: true
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
                    controller.startWindowDrag();
                    window.isDragging = false;
                    window.wasDragged = false;
                } else if (mouse.button === Qt.RightButton) {
                    controller.toggleDetailed();
                }
            }

            onPositionChanged: function(mouse) {
                if (mouse.buttons & Qt.LeftButton) {
                    var npos = controller.updateWindowDrag();
                    var nx = npos[0];
                    var ny = npos[1];
                    if (Math.abs(nx - window.x) > 2 || Math.abs(ny - window.y) > 2) {
                        window.isDragging = true;
                        window.wasDragged = true;
                        window.x = nx;
                        window.y = ny;
                    }
                }
            }

            onReleased: function(mouse) {
                if (mouse.button === Qt.LeftButton) {
                    if (window.wasDragged) {
                        window.endDragAndClamp();
                    } else {
                        // Immediate, responsive view cycle on click
                        controller.cycleView();
                    }
                }
            }
        }
    }
}
