import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // In Tkinter: cy = h // 2; dot at (20, cy); dot img is 28x28 centered at 20 => cx=20, cy=21
    StatusDot {
        id: statusDot
        x: 10
        anchors.verticalCenter: parent.verticalCenter
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // In Tkinter: text at (36, cy), anchor='w', font=(FONT_NAME, 9, 'bold'), HEX_TEXT_SECONDARY (#A1A1A6)
    Text {
        id: modelText
        x: 36
        anchors.verticalCenter: parent.verticalCenter
        text: controller.cleanLatestModel
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
        elide: Text.ElideRight
        width: metricsText.x - 36 - 12
    }

    // In Tkinter: text at (w - 24, cy), anchor='e', font=(FONT_NAME, 9, 'bold')
    Text {
        id: metricsText
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        color: {
            if (controller.flyingDeltaText !== "") return "#30D158";
            if (controller.isHovered && controller.latestTps > 0) return "#FF9F0A";
            return "#FFFFFF";
        }
        font.family: "SF Pro Display"
        font.pixelSize: 9
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
