from PySide6.QtCore import QObject, Signal, Property, Slot
from PySide6.QtGui import QGuiApplication

class ScalingService(QObject):
    dprChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dpr = 1.0
        self.update_dpr()

    def update_dpr(self, screen=None):
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        new_dpr = 1.0
        if hasattr(screen, 'devicePixelRatio'):
            new_dpr = screen.devicePixelRatio()
        elif screen is not None:
            # Check primary screen
            ps = QGuiApplication.primaryScreen()
            if ps:
                new_dpr = ps.devicePixelRatio()
        if abs(self._dpr - new_dpr) > 0.001:
            self._dpr = new_dpr
            self.dprChanged.emit()

    @Property(float, notify=dprChanged)
    def dpr(self):
        return self._dpr

    @Slot(float, result=float)
    def toLogical(self, physical_px):
        """Converts legacy Tkinter physical pixel dimension to Qt logical dimension."""
        return physical_px / self._dpr

    @Slot(float, result=float)
    def toPhysical(self, logical_px):
        """Converts Qt logical dimension to physical screen pixel dimension."""
        return logical_px * self._dpr

    @Slot(float, result=int)
    def dp(self, physical_px):
        """Returns rounded integer logical coordinate for exact alignment."""
        return int(round(physical_px / self._dpr))

    @Slot(float, result=float)
    def sp(self, font_size_px):
        """Font scale factor: preserves exact Tkinter visual typographic weight."""
        return font_size_px / self._dpr
