import QtQuick
import "."

Item {
    id: root

    function dp(px) { return controller.scaler.dp(px); }
    function sp(px) { return controller.scaler.sp(px); }

    // Status Dot on Left: x = dp(20), cy = parent.height / 2
    StatusDot {
        id: statusDot
        x: root.dp(20) - (width / 2)
        anchors.verticalCenter: parent.verticalCenter
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // Model Name: x = dp(36), cy = parent.height / 2, font=(FONT_NAME, 9, 'bold'), HEX_TEXT_SECONDARY (#A1A1A6)
    Text {
        id: modelText
        x: root.dp(36)
        anchors.verticalCenter: parent.verticalCenter
        text: controller.minShortModel
        color: "#9ca3af"
        font.family: "SF Pro Display"
        font.pointSize: 9
        font.bold: true
        elide: Text.ElideRight
        width: Math.max(0, metricsText.x - root.dp(36) - root.dp(8))
    }

    // Right-hand Metrics / Hover Peek / Flying delta: rightMargin = dp(16)
    Text {
        id: metricsText
        anchors.right: parent.right
        anchors.rightMargin: root.dp(16)
        anchors.verticalCenter: parent.verticalCenter
        clip: true
        color: {
            if (controller.flyingDeltaText !== "") return "#30D158";
            if (controller.isHovered) return "#f59e0b";
            return "#FFFFFF";
        }
        font.family: "SF Pro Display"
        font.pointSize: 9
        font.bold: true
        visible: true
        text: {
            if (controller.flyingDeltaText !== "") {
                return controller.flyingDeltaText;
            }
            if (controller.isHovered) {
                var peekParts = [];
                if (controller.latestTpsStr !== "") peekParts.push(controller.latestTpsStr);
                if (controller.primaryResetTimeLeft !== "") peekParts.push("Resets " + controller.primaryResetTimeLeft);
                if (peekParts.length > 0) return peekParts.join(" • ");
                return "Peek Ready";
            }
            return controller.totalTokensStr + " tok • " + controller.costStr;
        }
    }
}
