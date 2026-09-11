import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // Status Dot on Left
    StatusDot {
        id: statusDot
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // Model Name
    Text {
        id: modelText
        anchors.left: statusDot.right
        anchors.leftMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: metricsText.left
        anchors.rightMargin: 8
        text: controller.cleanLatestModel
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 10
        font.bold: true
        elide: Text.ElideRight
    }

    // Right-hand Metrics / Hover Peek / Flying delta
    Text {
        id: metricsText
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        color: {
            if (controller.flyingDeltaText !== "") return "#30D158";
            if (controller.isHovered && controller.latestTps > 0) return "#FF9F0A";
            return "#FFFFFF";
        }
        font.family: "SF Pro Display"
        font.pixelSize: 10
        font.bold: true
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
