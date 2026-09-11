import QtQuick
import "."

Item {
    id: root
    anchors.fill: parent

    // In Tkinter: place_dot(22, 24)
    StatusDot {
        id: statusDot
        x: 12
        y: 14
        active: controller.isActivityActive
        error: controller.isActivityError
    }

    // In Tkinter: canvas.create_text(40, 24, anchor='w', text=raw_m, font=(FONT_NAME, 10, 'bold'), fill=HEX_TEXT_PRIMARY)
    Text {
        id: modelTitle
        x: 40
        y: 24 - (implicitHeight / 2)
        text: controller.cleanLatestModel
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 10
        font.bold: true
        elide: Text.ElideRight
        width: timelineTabs.x - 40 - 12
    }

    // In Tkinter: render_timeline_tabs(w - 22, 24, anchor='e')
    TimelineTabs {
        id: timelineTabs
        anchors.right: parent.right
        anchors.rightMargin: 22
        anchors.verticalCenter: modelTitle.verticalCenter
        currentTimeline: controller.timeline
        onTimelineSelected: function(key) {
            controller.setTimeline(key);
        }
    }

    // In Tkinter: canvas.create_text(22, 64, anchor='w', text=f"{format_num(tot_tok)} Tokens", font=(FONT_NAME, 16, 'bold'))
    Text {
        id: bigTokens
        x: 22
        y: 64 - (implicitHeight / 2)
        text: controller.totalTokensStr + " Tokens"
        color: "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 16
        font.bold: true
    }

    // In Tkinter: canvas.create_text(w - 22, 64, anchor='e', text=norm_right_text, font=(FONT_NAME, 12, 'bold'))
    Text {
        id: costAndReqs
        anchors.right: parent.right
        anchors.rightMargin: 22
        y: 64 - (implicitHeight / 2)
        color: controller.flyingDeltaText !== "" ? "#30D158" : "#FFFFFF"
        font.family: "SF Pro Display"
        font.pixelSize: 12
        font.bold: true
        text: controller.flyingDeltaText !== "" ? controller.flyingDeltaText : (controller.costStr + "  |  " + controller.requestsStr + " reqs")
    }

    // In Tkinter: canvas.create_text(22, 104, anchor='w', text=ticker_txt, font=(FONT_NAME, 9), tags='norm_ticker')
    Text {
        id: tickerLabel
        x: 22
        y: 104 - (implicitHeight / 2)
        anchors.right: expandHint.left
        anchors.rightMargin: 12
        text: controller.tickerText
        color: "#A1A1A6"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        elide: Text.ElideRight
    }

    // In Tkinter: canvas.create_text(w - 22, 104, anchor='e', text='Full', font=(FONT_NAME, 9, 'bold'), fill=HEX_TEXT_MUTED)
    Text {
        id: expandHint
        anchors.right: parent.right
        anchors.rightMargin: 22
        y: 104 - (implicitHeight / 2)
        text: "Full"
        color: "#58585E"
        font.family: "SF Pro Display"
        font.pixelSize: 9
        font.bold: true
    }
}
