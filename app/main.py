import os
import sys
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QGuiApplication, QFontDatabase, QIcon
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQml import QQmlApplicationEngine
from app.backend.hud_controller import HUDController

def main():
    # 1. High-DPI and transparency buffer setup
    QQuickWindow.setDefaultAlphaBuffer(True)
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Dynamic Token HUD")
    app.setOrganizationName("DynamicToken")

    # 2. Register Apple SF Pro Display fonts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(base_dir, "..", "fonts")
    if not os.path.exists(fonts_dir):
        fonts_dir = os.path.join(base_dir, "resources", "fonts")
    
    if os.path.exists(fonts_dir):
        for font_file in os.listdir(fonts_dir):
            if font_file.endswith((".otf", ".ttf")):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, font_file))

    # 3. Create Backend Controller
    controller = HUDController()

    # 4. Setup QML Application Engine
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("controller", controller)

    qml_file = os.path.join(base_dir, "ui", "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        print("Error: Failed to load QML root object.")
        sys.exit(-1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
