import QtQuick

Item {
    id: root
    property real cornerRadius: 21
    property bool isDockedNotch: false
    property bool isHovered: false
    property bool isActivityActive: false
    property bool isActivityError: false
    clip: true

    readonly property color baseBorderColor: root.isHovered ? "#444448" : "#262629"
    readonly property color glowColor: root.isActivityError ? "#FF453A" : "#30D158"

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        property real glowOpacity: root.isActivityActive ? 0.85 : 0.0
        Behavior on glowOpacity {
            NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
        }

        onGlowOpacityChanged: requestPaint()

        Connections {
            target: root
            function onCornerRadiusChanged() { canvas.requestPaint(); }
            function onIsDockedNotchChanged() { canvas.requestPaint(); }
            function onIsHoveredChanged() { canvas.requestPaint(); }
            function onIsActivityActiveChanged() { canvas.requestPaint(); }
            function onIsActivityErrorChanged() { canvas.requestPaint(); }
            function onWidthChanged() { canvas.requestPaint(); }
            function onHeightChanged() { canvas.requestPaint(); }
        }

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();

            var w = width;
            var h = height;
            var r = root.cornerRadius;

            // 1. Fill pitch black body
            ctx.fillStyle = "#000000";
            ctx.beginPath();
            if (root.isDockedNotch) {
                // Notch: sharp top corners flush to screen top, rounded bottom corners
                ctx.moveTo(0, 0);
                ctx.lineTo(w, 0);
                ctx.lineTo(w, h - r);
                ctx.arcTo(w, h, w - r, h, r);
                ctx.lineTo(r, h);
                ctx.arcTo(0, h, 0, h - r, r);
                ctx.lineTo(0, 0);
            } else {
                // Floating capsule: 4 rounded corners
                ctx.moveTo(r, 0);
                ctx.lineTo(w - r, 0);
                ctx.arcTo(w, 0, w, r, r);
                ctx.lineTo(w, h - r);
                ctx.arcTo(w, h, w - r, h, r);
                ctx.lineTo(r, h);
                ctx.arcTo(0, h, 0, h - r, r);
                ctx.lineTo(0, r);
                ctx.arcTo(0, 0, r, 0, r);
            }
            ctx.closePath();
            ctx.fill();

            // 2. Stroke 1px base border
            ctx.strokeStyle = root.baseBorderColor;
            ctx.lineWidth = 1;
            ctx.lineJoin = "miter";
            ctx.miterLimit = 4;
            ctx.beginPath();
            if (root.isDockedNotch) {
                ctx.moveTo(0.5, 0.5);
                ctx.lineTo(w - 0.5, 0.5);
                ctx.lineTo(w - 0.5, h - r);
                ctx.arcTo(w - 0.5, h - 0.5, w - r, h - 0.5, r);
                ctx.lineTo(r, h - 0.5);
                ctx.arcTo(0.5, h - 0.5, 0.5, h - r, r);
                ctx.lineTo(0.5, 0.5);
            } else {
                ctx.moveTo(r, 0.5);
                ctx.lineTo(w - r, 0.5);
                ctx.arcTo(w - 0.5, 0.5, w - 0.5, r, r);
                ctx.lineTo(w - 0.5, h - r);
                ctx.arcTo(w - 0.5, h - 0.5, w - r, h - 0.5, r);
                ctx.lineTo(r, h - 0.5);
                ctx.arcTo(0.5, h - 0.5, 0.5, h - r, r);
                ctx.lineTo(0.5, r);
                ctx.arcTo(0.5, 0.5, r, 0.5, r);
            }
            ctx.closePath();
            ctx.stroke();

            // 3. Stroke Specular Activity Rim Glow (following identical attached border path)
            if (root.isActivityActive) {
                ctx.save();
                ctx.strokeStyle = root.glowColor;
                ctx.lineWidth = 2.0;
                ctx.lineJoin = "miter";
                ctx.miterLimit = 4;
                ctx.beginPath();
                if (root.isDockedNotch) {
                    ctx.moveTo(1.0, 1.0);
                    ctx.lineTo(w - 1.0, 1.0);
                    ctx.lineTo(w - 1.0, h - r);
                    ctx.arcTo(w - 1.0, h - 1.0, w - r, h - 1.0, r);
                    ctx.lineTo(r, h - 1.0);
                    ctx.arcTo(1.0, h - 1.0, 1.0, h - r, r);
                    ctx.lineTo(1.0, 1.0);
                } else {
                    ctx.moveTo(r, 1.0);
                    ctx.lineTo(w - r, 1.0);
                    ctx.arcTo(w - 1.0, 1.0, w - 1.0, r, r);
                    ctx.lineTo(w - 1.0, h - r);
                    ctx.arcTo(w - 1.0, h - 1.0, w - r, h - 1.0, r);
                    ctx.lineTo(r, h - 1.0);
                    ctx.arcTo(1.0, h - 1.0, 1.0, h - r, r);
                    ctx.lineTo(1.0, r);
                    ctx.arcTo(1.0, 1.0, r, 1.0, r);
                }
                ctx.closePath();
                ctx.stroke();
                ctx.restore();
            }
        }
    }
}
