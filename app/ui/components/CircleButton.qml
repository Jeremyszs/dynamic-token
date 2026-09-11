import QtQuick

Rectangle {
    id: root
    property string iconType: "text" // "text", "close", "minimize", "left", "right"
    property string buttonText: ""
    property color normalColor: "#1C1C1E"
    property color hoverColor: "#2C2C30"
    property color pressColor: "#151517"
    property color borderColor: "#262629"
    property color iconColor: "#FFFFFF"
    property int radiusSize: 12
    signal clicked()

    width: radiusSize * 2
    height: radiusSize * 2
    radius: radiusSize
    color: mouseArea.pressed ? pressColor : (mouseArea.containsMouse ? hoverColor : normalColor)
    border.color: borderColor
    border.width: 1

    Behavior on color {
        ColorAnimation { duration: 120 }
    }

    Text {
        anchors.centerIn: parent
        visible: root.iconType === "text"
        text: root.buttonText
        color: root.iconColor
        font.family: "SF Pro Display"
        font.pixelSize: 10
        font.bold: true
    }

    // Vector Chevron Left
    Canvas {
        anchors.fill: parent
        visible: root.iconType === "left"
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.strokeStyle = root.iconColor;
            ctx.lineWidth = 1.6;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            var cx = width / 2;
            var cy = height / 2;
            ctx.beginPath();
            ctx.moveTo(cx + 2, cy - 4);
            ctx.lineTo(cx - 2, cy);
            ctx.lineTo(cx + 2, cy + 4);
            ctx.stroke();
        }
    }

    // Vector Chevron Right
    Canvas {
        anchors.fill: parent
        visible: root.iconType === "right"
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.strokeStyle = root.iconColor;
            ctx.lineWidth = 1.6;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            var cx = width / 2;
            var cy = height / 2;
            ctx.beginPath();
            ctx.moveTo(cx - 2, cy - 4);
            ctx.lineTo(cx + 2, cy);
            ctx.lineTo(cx - 2, cy + 4);
            ctx.stroke();
        }
    }

    // Vector Close (Geometric cross)
    Canvas {
        anchors.fill: parent
        visible: root.iconType === "close"
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.strokeStyle = root.iconColor;
            ctx.lineWidth = 2;
            ctx.lineCap = "round";
            var cx = width / 2;
            var cy = height / 2;
            var d = 4;
            ctx.beginPath();
            ctx.moveTo(cx - d, cy - d);
            ctx.lineTo(cx + d, cy + d);
            ctx.moveTo(cx - d, cy + d);
            ctx.lineTo(cx + d, cy - d);
            ctx.stroke();
        }
    }

    // Vector Minimize
    Canvas {
        anchors.fill: parent
        visible: root.iconType === "minimize"
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.strokeStyle = root.iconColor;
            ctx.lineWidth = 2;
            ctx.lineCap = "round";
            var cx = width / 2;
            var cy = height / 2;
            ctx.beginPath();
            ctx.moveTo(cx - 4, cy);
            ctx.lineTo(cx + 4, cy);
            ctx.stroke();
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
