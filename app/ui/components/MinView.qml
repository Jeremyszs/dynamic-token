import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // Status Dot on Left at x=14
    StatusDot {
        id: statusDot
        x: 14
        anchors.verticalCenter: parent.verticalCenter
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // Model Name: e.g. "3.8-fhigh" in neutral gray (#9ca3af), 9pt bold
    Text {
        id: modelText
        x: 32
        anchors.verticalCenter: parent.verticalCenter
        text: controller.cleanLatestModel
        color: "#9ca3af"
        font.family: "SF Pro Display"
        font.pixelSize: 11
        font.bold: true
        elide: Text.ElideRight
        width: metricsText.x - 32 - 10
    }

    // Right-hand Metrics / Hover Peek / Flying delta
    Text {
        id: metricsText
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        color: {
            if (controller.flyingDeltaText !== "") return "#30D158";
            if (controller.isHovered || controller.latestTps > 0) return "#f59e0b"; // Exact orange from Tkinter
            return "#FFFFFF";
        }
        font.family: "SF Pro Display"
        font.pixelSize: 11
        font.bold: true
        text: {
            if (controller.flyingDeltaText !== "") {
                return controller.flyingDeltaText;
            }
            // If hovering OR active generation, show the exact orange string: "183 tok/s • Resets 2h 36m"
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
