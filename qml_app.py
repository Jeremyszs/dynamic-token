import os
import sys
import json
import sqlite3
import datetime
from PySide6 import QtCore, QtGui, QtQuick, QtQml
import win32gui
import win32con
import win32api

DB_PATH = os.path.expandvars(r'%APPDATA%\9router\db\data.sqlite')
CONFIG_PATH = os.path.expandvars(r'%LOCALAPPDATA%\hermes\dynamic_island_config.json')

VIEW_SPECS = {
    'min': (320, 42, 21),
    'normal': (520, 136, 26),
    'detailed': (620, 430, 28)
}

def format_num(n):
    if n is None:
        return '0'
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))

def format_time_ago(ts_str):
    if not ts_str:
        return '--'
    try:
        cleaned = ts_str.replace('Z', '+00:00')
        dt = datetime.datetime.fromisoformat(cleaned)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = int((now - dt).total_seconds())
        if diff < 5:
            return 'just now'
        if diff < 60:
            return f"{diff}s ago"
        if diff < 3600:
            return f"{diff // 60}m ago"
        return f"{diff // 3600}h ago"
    except Exception:
        return ts_str[11:19] if len(ts_str) >= 19 else ts_str

class IslandBackend(QtCore.QObject):
    statsChanged = QtCore.Signal()
    viewChanged = QtCore.Signal()

    def __init__(self, window):
        super().__init__()
        self.window = window
        self._current_view = 'min'
        self._timeline = 'today'
        self._stats = {
            'requests': 0, 'prompt': 0, 'completion': 0, 'cached': 0,
            'cost': 0.0, 'models': {}, 'recent': [], 'latest_model': '--'
        }
        self.load_config()

        self._drag_start_pos = QtCore.QPoint(0, 0)
        self._orig_win_pos = QtCore.QPoint(0, 0)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.fetch_database_data)
        self.timer.start(1000)

        self.fetch_database_data()

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    cfg = json.load(f)
                    self._current_view = cfg.get('view', 'min')
                    self._timeline = cfg.get('timeline', 'today')
            except Exception:
                pass

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            pos = self.window.position()
            with open(CONFIG_PATH, 'w') as f:
                json.dump({
                    'x': pos.x(),
                    'y': pos.y(),
                    'view': self._current_view,
                    'timeline': self._timeline
                }, f)
        except Exception:
            pass

    @QtCore.Property(str, notify=viewChanged)
    def currentView(self):
        return self._current_view

    @QtCore.Property(str, notify=statsChanged)
    def timeline(self):
        return self._timeline

    @QtCore.Property(str, notify=statsChanged)
    def shortModel(self):
        raw_m = self._stats.get('latest_model', '--')
        short_m = raw_m.replace('gemini-', '').replace('flash-', 'f').replace('thinking', 'thk')
        return short_m[:12] + '..' if len(short_m) > 14 else short_m

    @QtCore.Property(str, notify=statsChanged)
    def latestModel(self):
        return self._stats.get('latest_model', '--')

    @QtCore.Property(str, notify=statsChanged)
    def totalTokensStr(self):
        tot = self._stats.get('prompt', 0) + self._stats.get('completion', 0)
        return format_num(tot)

    @QtCore.Property(str, notify=statsChanged)
    def costStr(self):
        return f"${self._stats.get('cost', 0.0):.2f}"

    @QtCore.Property(str, notify=statsChanged)
    def requestsStr(self):
        return format_num(self._stats.get('requests', 0))

    @QtCore.Property(str, notify=statsChanged)
    def cacheRatioStr(self):
        prompt = self._stats.get('prompt', 0)
        cached = self._stats.get('cached', 0)
        pct = (cached / prompt * 100) if prompt > 0 else 0.0
        return f"{pct:.1f}%"

    @QtCore.Property(str, notify=statsChanged)
    def tickerText(self):
        recent = self._stats.get('recent', [])
        if recent:
            last = recent[0]
            t_ago = format_time_ago(last[1])
            tot = last[4] + last[5]
            return f"Last: {t_ago} • {last[3]} • +{format_num(tot)} tok"
        return "Listening for API calls..."

    @QtCore.Property('QVariantList', notify=statsChanged)
    def modelsModel(self):
        tot = self._stats.get('prompt', 0) + self._stats.get('completion', 0)
        sorted_m = sorted(self._stats.get('models', {}).items(), key=lambda x: x[1]['prompt'], reverse=True)[:3]
        res = []
        for name, data in sorted_m:
            p_val = data['prompt'] + data['completion']
            r_val = data['requests']
            ratio = min(1.0, p_val / (tot if tot > 0 else 1))
            res.append({
                'name': name,
                'usage': f"{format_num(p_val)} tok ({r_val} reqs)",
                'ratio': ratio
            })
        return res

    @QtCore.Property('QVariantList', notify=statsChanged)
    def historyModel(self):
        res = []
        for row in self._stats.get('recent', [])[:3]:
            # (id, timestamp, provider, model, promptTokens, completionTokens, cost, status)
            t_ago = format_time_ago(row[1])
            toks = row[4] + row[5]
            res.append({
                'status': row[7],
                'model': row[3],
                'tokens': format_num(toks),
                'time': t_ago
            })
        return res

    @QtCore.Slot(str)
    def setTimeline(self, tl):
        self._timeline = tl
        self.fetch_database_data()
        self.save_config()

    @QtCore.Slot(str)
    def setView(self, v):
        if v in VIEW_SPECS:
            self._current_view = v
            self.viewChanged.emit()
            self.adjust_window_size()
            self.save_config()

    @QtCore.Slot()
    def cycleView(self):
        order = ['min', 'normal', 'detailed']
        next_v = order[(order.index(self._current_view) + 1) % len(order)]
        self.setView(next_v)

    @QtCore.Slot()
    def toggleDetailed(self):
        self.setView('detailed' if self._current_view == 'min' else 'min')

    @QtCore.Slot()
    def shutdown(self):
        self.save_config()
        QtCore.QCoreApplication.quit()

    @QtCore.Slot(int, int)
    def startDrag(self, mx, my):
        self._drag_start_pos = QtGui.QCursor.pos()
        self._orig_win_pos = self.window.position()

    @QtCore.Slot(int, int)
    def dragWindow(self, mx, my):
        cur_pos = QtGui.QCursor.pos()
        dx = cur_pos.x() - self._drag_start_pos.x()
        dy = cur_pos.y() - self._drag_start_pos.y()
        self.window.setPosition(self._orig_win_pos.x() + dx, self._orig_win_pos.y() + dy)

    @QtCore.Slot()
    def savePosition(self):
        self.save_config()

    def adjust_window_size(self):
        tw, th, _ = VIEW_SPECS[self._current_view]
        pos = self.window.position()
        cur_w = self.window.width()
        cur_h = self.window.height()

        # Multi-monitor bounds check
        hwnd = int(self.window.winId())
        try:
            hmon = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            info = win32api.GetMonitorInfo(hmon)
            m_left, m_top, m_right, m_bottom = info['Work']
        except Exception:
            m_left, m_top, m_right, m_bottom = 0, 0, 1920, 1080

        center_x = pos.x() + cur_w / 2.0
        new_x = max(m_left + 10, min(m_right - tw - 10, int(center_x - tw / 2.0)))
        new_y = max(m_top + 10, min(m_bottom - th - 10, pos.y()))

        self.window.setGeometry(new_x, new_y, tw, th)

    def fetch_database_data(self):
        if not os.path.exists(DB_PATH):
            return
        try:
            con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
            cur = con.cursor()
            today_str = datetime.date.today().isoformat()
            if self._timeline == 'today':
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey = ?', (today_str,)).fetchall()
            elif self._timeline == '7d':
                start_str = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey >= ?', (start_str,)).fetchall()
            elif self._timeline == '30d':
                start_str = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey >= ?', (start_str,)).fetchall()
            else:
                rows = cur.execute('SELECT dateKey, data FROM usageDaily').fetchall()

            reqs = 0
            prompt = 0
            comp = 0
            cached = 0
            cost = 0.0
            by_model = {}

            for r in rows:
                try:
                    d = json.loads(r[1])
                    reqs += d.get('requests', 0)
                    prompt += d.get('promptTokens', 0)
                    comp += d.get('completionTokens', 0)
                    cached += d.get('cachedTokens', 0)
                    cost += d.get('cost', 0.0)
                    for m_key, mstat in d.get('byModel', {}).items():
                        clean = m_key.split('|')[0]
                        if clean not in by_model:
                            by_model[clean] = {'requests': 0, 'prompt': 0, 'completion': 0, 'cached': 0, 'cost': 0.0}
                        by_model[clean]['requests'] += mstat.get('requests', 0)
                        by_model[clean]['prompt'] += mstat.get('promptTokens', 0)
                        by_model[clean]['completion'] += mstat.get('completionTokens', 0)
                        by_model[clean]['cached'] += mstat.get('cachedTokens', 0)
                        by_model[clean]['cost'] += mstat.get('cost', 0.0)
                except Exception:
                    pass

            recent_rows = cur.execute(
                'SELECT id, timestamp, provider, model, promptTokens, completionTokens, cost, status FROM usageHistory ORDER BY id DESC LIMIT 5'
            ).fetchall()

            latest_m = recent_rows[0][3] if recent_rows else '--'

            self._stats = {
                'requests': reqs,
                'prompt': prompt,
                'completion': comp,
                'cached': cached,
                'cost': cost,
                'models': by_model,
                'recent': recent_rows,
                'latest_model': latest_m
            }
            con.close()
            self.statsChanged.emit()
        except Exception:
            pass

def main():
    # Enable true high-DPI scaling & hardware VSync
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

    app = QtGui.QGuiApplication(sys.argv)

    # Register Apple Fonts
    font_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    if os.path.exists(font_dir):
        for f in os.listdir(font_dir):
            if f.endswith(('.otf', '.ttf')):
                QtGui.QFontDatabase.addApplicationFont(os.path.join(font_dir, f))

    # Create Frameless, Layered Transparent QuickView
    view = QtQuick.QQuickView()
    view.setColor(QtGui.QColor(0, 0, 0, 0)) # 100% transparent surface

    # Flags: Frameless, Always-On-Top, ToolWindow
    view.setFlags(
        QtCore.Qt.FramelessWindowHint |
        QtCore.Qt.WindowStaysOnTopHint |
        QtCore.Qt.Tool |
        QtCore.Qt.NoDropShadowWindowHint
    )

    # Load initial geometry from config or center
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                cfg = json.load(f)
        except Exception:
            pass

    curr_v = cfg.get('view', 'min')
    w, h, _ = VIEW_SPECS[curr_v]
    x = cfg.get('x', 600)
    y = cfg.get('y', 20)

    view.setGeometry(x, y, w, h)

    backend = IslandBackend(view)
    view.rootContext().setContextProperty('backend', backend)

    qml_path = os.path.join(os.path.dirname(__file__), 'qml', 'main.qml')
    view.setSource(QtCore.QUrl.fromLocalFile(qml_path))
    view.setResizeMode(QtQuick.QQuickView.SizeRootObjectToView)

    view.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
