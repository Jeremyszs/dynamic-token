from PySide6.QtCore import QObject, QPoint, QRect, Slot
from PySide6.QtGui import QGuiApplication


class WindowPositionService(QObject):
    """
    Centralized window bounds clamping utility for PySide6 + Qt Quick desktop widgets.
    Respects per-monitor availableGeometry() (usable workarea minus taskbars),
    handles multi-monitor setups with negative coordinates, differing resolutions & DPIs,
    and calculates minimal clamp corrections.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    @staticmethod
    def get_screen_at_geometry(x: int, y: int, w: int, h: int):
        app = QGuiApplication.instance()
        if not app:
            return None

        # Calculate overlap area with each screen to find the screen containing the largest portion of the widget
        widget_rect = QRect(int(x), int(y), int(w), int(h))
        best_scr = None
        max_overlap = 0

        for s in app.screens():
            inter = widget_rect.intersected(s.geometry())
            area = inter.width() * inter.height() if (not inter.isEmpty()) else 0
            if area > max_overlap:
                max_overlap = area
                best_scr = s

        if best_scr and max_overlap > 0:
            return best_scr

        # If completely outside all screens, find the nearest screen by distance to widget center
        cx = int(x + (w / 2.0))
        cy = int(y + (h / 2.0))
        min_dist_sq = float('inf')
        best_scr = app.primaryScreen()

        for s in app.screens():
            sg = s.geometry()
            scx = sg.x() + (sg.width() / 2.0)
            scy = sg.y() + (sg.height() / 2.0)
            dist_sq = (cx - scx) ** 2 + (cy - scy) ** 2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_scr = s

        return best_scr

    @classmethod
    def clamp_rect_to_screen(cls, x: int, y: int, w: int, h: int, is_docked_notch: bool = False):
        """
        Clamps (x, y) so a widget of size (w, h) remains completely within the
        usable availableGeometry of its active screen.

        Returns: (clamped_x, clamped_y, is_docked_top, screen_ref)
        """
        scr = cls.get_screen_at_geometry(x, y, w, h)
        if not scr:
            return int(x), int(y), False, None

        avail: QRect = scr.availableGeometry()
        s_left = avail.left()
        s_top = avail.top()
        s_right = avail.right() + 1      # inclusive right boundary
        s_bottom = avail.bottom() + 1    # inclusive bottom boundary

        clamped_x = int(x)
        clamped_y = int(y)

        # Horizontal clamping
        if w >= avail.width():
            # Edge case: widget is wider than available screen width -> anchor to left
            clamped_x = s_left
        else:
            if clamped_x < s_left:
                clamped_x = s_left
            elif clamped_x + w > s_right:
                clamped_x = s_right - w

        # Vertical clamping: keep fully inside usable workarea
        if h >= avail.height():
            clamped_y = s_top
        else:
            if clamped_y < s_top:
                clamped_y = s_top
            elif clamped_y + h > s_bottom:
                clamped_y = s_bottom - h

        # Check magnetic screen-top notch docking ONLY when user actually releases within 16px of top edge
        dist_to_top = abs(y - s_top)
        docked_top = False
        if dist_to_top <= 16:
            clamped_y = s_top
            docked_top = True

        return clamped_x, clamped_y, docked_top, scr
