import os
import json
import time
import datetime
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
from PySide6.QtGui import QGuiApplication, QCursor
from .data_service import DataService
from .system_integration import check_startup_registration, check_9router_health, run_9router
from .models import format_num, format_time_ago, format_time_left, clean_model_display_name
from .scaling_service import ScalingService
from .window_position_service import WindowPositionService

CONFIG_PATH = os.path.expandvars(r'%LOCALAPPDATA%\hermes\dynamic_island_config.json')

# EXACT LEGACY TKINTER PHYSICAL DIMENSIONS (Source of Truth)
TKINTER_PHYSICAL_SPECS = {
    'min': (320, 42, 21),
    'normal': (520, 136, 26),
    'detailed': (660, 390, 28)
}

class HUDController(QObject):
    # Signals
    viewChanged = Signal()
    timelineChanged = Signal()
    statsChanged = Signal()
    routerStatusChanged = Signal()
    splitActiveChanged = Signal()
    dockedNotchChanged = Signal()
    hoveredChanged = Signal()
    requestWindowResize = Signal(int, int, int) # w, h, radius
    requestWindowMove = Signal(int, int)       # x, y

    def __init__(self):
        super().__init__()
        self.scaling = ScalingService(self)
        self.data_service = DataService(on_data_updated=self._on_background_data_ready)
        
        self._current_view = 'min'
        self._timeline = 'today'
        self._is_hovered = False
        self._is_docked_notch = False
        self._is_9router_running = False
        self._is_split_active = False

        self._target_x = 450
        self._target_y = 40

        self.stats = {
            'requests': 0, 'prompt': 0, 'completion': 0, 'cached': 0, 'reasoning': 0,
            'cost': 0.0, 'models': {}, 'recent': [], 'latest_model': '--',
            'latest_latency': None, 'providers_data': [], 'latest_conn_id': None
        }

        self.load_config()
        check_startup_registration()

        # Timers
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_tick)
        self.poll_timer.start(1000)

        # Initial fetch
        self.check_health()
        self.refresh_stats()

    @Slot(QObject)
    def updateScreenDpr(self, screen_obj):
        if screen_obj:
            self.scaling.update_dpr(screen_obj)

    def set_window(self, window):
        self._window = window
        self._drag_cursor_offset_x = 0
        self._drag_cursor_offset_y = 0

    @Slot()
    def startWindowDrag(self):
        """
        Records the cursor offset relative to window position in logical screen coordinates.
        Absolute tracking guarantees zero feedback loops, zero delta accumulation errors, and zero flickering.
        """
        if not self._window:
            return
        cur = QCursor.pos()
        self._drag_cursor_offset_x = cur.x() - self._window.x()
        self._drag_cursor_offset_y = cur.y() - self._window.y()

    @Slot(result=list)
    def updateWindowDrag(self):
        """
        Returns the new absolute [target_x, target_y] based on current global cursor position.
        """
        cur = QCursor.pos()
        nx = cur.x() - self._drag_cursor_offset_x
        ny = cur.y() - self._drag_cursor_offset_y
        return [nx, ny]

    @Property(QObject, constant=True)
    def scaler(self):
        return self.scaling

    @Property(int, notify=viewChanged)
    def targetWidth(self):
        pw, _, _ = TKINTER_PHYSICAL_SPECS[self._current_view]
        # Stretch min view when hovered with cursor (320px -> 350px physical)
        if self._current_view == 'min' and self._is_hovered:
            pw = 350
        # When split island bubble is ejected, expand window so both main capsule and split bubble fit with all metrics visible
        if self._current_view == 'min' and self._is_split_active:
            pw += 70
        return self.scaling.dp(pw)

    @Property(int, notify=viewChanged)
    def targetHeight(self):
        _, ph, _ = TKINTER_PHYSICAL_SPECS[self._current_view]
        return self.scaling.dp(ph)

    @Property(int, notify=viewChanged)
    def targetRadius(self):
        _, _, pr = TKINTER_PHYSICAL_SPECS[self._current_view]
        return self.scaling.dp(pr)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    cfg = json.load(f)
                    self._target_x = cfg.get('x', 450)
                    self._target_y = cfg.get('y', 40)
                    self._current_view = cfg.get('view', 'min')
                    self._timeline = cfg.get('timeline', 'today')
                    self._is_docked_notch = cfg.get('docked_notch', False)

                # Validate and clamp loaded position against active screen
                pw, ph, _ = TKINTER_PHYSICAL_SPECS.get(self._current_view, (320, 42, 21))
                lw = self.scaling.dp(pw)
                lh = self.scaling.dp(ph)
                cx, cy, docked, _ = WindowPositionService.clamp_rect_to_screen(
                    self._target_x, self._target_y, lw, lh, is_docked_notch=self._is_docked_notch
                )
                self._target_x = cx
                self._target_y = cy
                self._is_docked_notch = docked
            except Exception:
                pass

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, 'w') as f:
                json.dump({
                    'x': int(self._target_x),
                    'y': int(self._target_y),
                    'view': self._current_view,
                    'timeline': self._timeline,
                    'docked_notch': self._is_docked_notch
                }, f)
        except Exception:
            pass

    def _on_background_data_ready(self):
        self.statsChanged.emit()

    def poll_tick(self):
        self.check_health()
        self.refresh_stats()

    def check_health(self):
        running = check_9router_health()
        if running != self._is_9router_running:
            self._is_9router_running = running
            self.routerStatusChanged.emit()

    def refresh_stats(self):
        new_stats = self.data_service.fetch_stats(timeline=self._timeline, is_9router_running=self._is_9router_running)
        if new_stats:
            self.stats = new_stats
            
            # Check split island activity
            time_since_call = time.time() - self.data_service.last_activity_time
            want_split = (self._current_view == 'min' and time_since_call < 3.5 and self.data_service.latest_tps is not None)
            if want_split != self._is_split_active:
                self.isSplitActive = want_split

            self.statsChanged.emit()

    # Properties
    @Property(str, notify=viewChanged)
    def currentView(self):
        return self._current_view

    @Property(str, notify=timelineChanged)
    def timeline(self):
        return self._timeline

    @Property(bool, notify=routerStatusChanged)
    def is9routerRunning(self):
        return self._is_9router_running

    @Property(bool, notify=splitActiveChanged)
    def isSplitActive(self):
        return self._is_split_active

    @isSplitActive.setter
    def isSplitActive(self, val):
        if self._is_split_active != val:
            self._is_split_active = val
            self.splitActiveChanged.emit()
            if self._current_view == 'min':
                self.viewChanged.emit()

    @Property(bool, notify=dockedNotchChanged)
    def isDockedNotch(self):
        return self._is_docked_notch

    @Property(bool, notify=hoveredChanged)
    def isHovered(self):
        return self._is_hovered

    @isHovered.setter
    def isHovered(self, val):
        if self._is_hovered != val:
            self._is_hovered = val
            self.hoveredChanged.emit()
            if self._current_view == 'min':
                self.viewChanged.emit()

    @Property(int, notify=viewChanged)
    def targetX(self):
        return self._target_x

    @Property(int, notify=viewChanged)
    def targetY(self):
        return self._target_y

    @Property(str, notify=statsChanged)
    def latestModel(self):
        return self.stats.get('latest_model', '--')

    @Property(str, notify=statsChanged)
    def cleanLatestModel(self):
        return clean_model_display_name(self.stats.get('latest_model', '--'))

    @Property(str, notify=statsChanged)
    def minShortModel(self):
        raw_m = self.stats.get('latest_model', '--')
        clean_m = clean_model_display_name(raw_m)
        return clean_m.replace('gemini-', '').replace('flash-', 'f').replace('thinking', 'thk')

    @Property(str, notify=statsChanged)
    def totalTokensStr(self):
        tot = self.stats.get('prompt', 0) + self.stats.get('completion', 0)
        return format_num(tot)

    @Property(str, notify=statsChanged)
    def costStr(self):
        return f"${self.stats.get('cost', 0.0):.2f}"

    @Property(str, notify=statsChanged)
    def requestsStr(self):
        return format_num(self.stats.get('requests', 0))

    @Property(str, notify=statsChanged)
    def cacheRatioStr(self):
        p = self.stats.get('prompt', 0)
        c = self.stats.get('cached', 0)
        pct = (c / p * 100.0) if p > 0 else 0.0
        return f"{pct:.1f}%"

    @Property(str, notify=statsChanged)
    def reasoningTokensStr(self):
        return format_num(self.stats.get('reasoning', 0))

    @Property(float, notify=statsChanged)
    def latestTps(self):
        return self.data_service.latest_tps or 0.0

    @Property(str, notify=statsChanged)
    def latestTpsStr(self):
        tps = self.data_service.latest_tps
        return f"{tps:.0f} tok/s" if tps else ""

    @Property(bool, notify=statsChanged)
    def isActivityActive(self):
        return (time.time() - self.data_service.last_activity_time) < 2.5

    @Property(bool, notify=statsChanged)
    def isActivityError(self):
        return self.data_service.last_activity_is_error

    @Property(str, notify=statsChanged)
    def latencySummaryStr(self):
        lat = self.stats.get('latest_latency')
        if not lat:
            return "-- ms"
        tot_ms = lat.get('total', 0)
        ttft_ms = lat.get('ttft', 0)
        tps_str = f" • {self.data_service.latest_tps:.0f} tok/s" if self.data_service.latest_tps else ""
        if tot_ms > 0:
            return f"{tot_ms / 1000.0:.2f}s (TTFT {ttft_ms}ms){tps_str}"
        return "-- ms"

    @Property(str, notify=statsChanged)
    def tickerText(self):
        recent = self.stats.get('recent', [])
        if recent:
            last = recent[0]
            t_ago = format_time_ago(last[1])
            m_cleaned = clean_model_display_name(last[3])
            toks = format_num(last[4] + last[5])
            lat_info = ""
            if self.stats.get('latest_latency'):
                tot_ms = self.stats['latest_latency'].get('total', 0)
                if tot_ms > 0:
                    lat_info = f" • {tot_ms / 1000.0:.1f}s"
            spd_info = f" • {self.data_service.latest_tps:.0f} tok/s" if self.data_service.latest_tps else ""
            return f"Last: {t_ago} • {m_cleaned} • +{toks} tok{lat_info}{spd_info}"
        return "Listening for API calls..."

    @Property(str, notify=statsChanged)
    def flyingDeltaText(self):
        diff = time.time() - self.data_service.last_delta_time
        if self.data_service.last_delta_time != 0 and diff < 1.8:
            return f"+{format_num(self.data_service.last_delta_tokens)} tok"
        return ""

    @Property(str, notify=statsChanged)
    def primaryResetTimeLeft(self):
        provs = self.stats.get('providers_data', [])
        if not provs:
            return ""
        curr_prov = provs[0]
        accs = curr_prov.get('accounts', [])
        if not accs:
            return ""
        target_acc = next((a for a in accs if a.get('is_current')), accs[0])
        cid = target_acc.get('id')
        live_data = self.data_service.fetch_live_quota(cid, self._is_9router_running)
        reset_at = None
        if live_data and 'quotas' in live_data:
            q_dict = live_data['quotas']
            latest_m = self.stats.get('latest_model', '')
            best_q = q_dict.get(latest_m) or q_dict.get('gemini-3.8-flash-high') or (next(iter(q_dict.values())) if q_dict else None)
            if best_q and 'resetAt' in best_q:
                reset_at = best_q['resetAt']
        if not reset_at and target_acc.get('reset_at'):
            reset_at = target_acc['reset_at']
        if not reset_at:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            reset_at = (now_utc + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return format_time_left(reset_at) or ""

    @Property('QVariantList', notify=statsChanged)
    def topModelsList(self):
        tot_tok = self.stats.get('prompt', 0) + self.stats.get('completion', 0)
        sorted_models = sorted(self.stats.get('models', {}).items(), key=lambda item: item[1]['prompt'], reverse=True)[:3]
        res = []
        for m_name, mdata in sorted_models:
            p_val = mdata['prompt'] + mdata['completion']
            r_val = mdata['requests']
            ratio = min(1.0, p_val / (tot_tok if tot_tok > 0 else 1))
            res.append({
                'raw_name': m_name,
                'clean_name': clean_model_display_name(m_name),
                'tokens_str': f"{format_num(p_val)} tok ({r_val} reqs)",
                'ratio': ratio
            })
        return res

    @Property('QVariantList', notify=statsChanged)
    def recentCallsList(self):
        res = []
        for row in self.stats.get('recent', [])[:3]:
            t_ago = format_time_ago(row[1])
            m_tag = clean_model_display_name(row[3])
            toks = row[4] + row[5]
            st = row[7]
            res.append({
                'model': m_tag,
                'status': '200 OK' if st == 'ok' else 'ERR',
                'is_ok': st == 'ok',
                'stats_str': f"+{format_num(toks)} tok • {t_ago}"
            })
        return res

    # Slots / Actions
    @Slot(str)
    def setView(self, view_name):
        if view_name not in TKINTER_PHYSICAL_SPECS:
            return
        self._current_view = view_name
        pw, ph, pr = TKINTER_PHYSICAL_SPECS[view_name]
        lw = self.scaling.dp(pw)
        lh = self.scaling.dp(ph)
        # Re-check screen bounds on view transition so larger views never bleed off screen
        cx, cy, docked, _ = WindowPositionService.clamp_rect_to_screen(
            self._target_x, self._target_y, lw, lh, is_docked_notch=self._is_docked_notch
        )
        self._target_x = cx
        self._target_y = cy
        if docked != self._is_docked_notch:
            self._is_docked_notch = docked
            self.dockedNotchChanged.emit()
        self.viewChanged.emit()
        self.requestWindowResize.emit(lw, lh, self.scaling.dp(pr))
        self.save_config()

    @Slot()
    def cycleView(self):
        order = ['min', 'normal', 'detailed']
        nxt = order[(order.index(self._current_view) + 1) % len(order)]
        self.setView(nxt)

    @Slot()
    def toggleDetailed(self):
        self.setView('min' if self._current_view == 'detailed' else 'detailed')

    @Slot(str)
    def setTimeline(self, key):
        if self._timeline != key:
            self._timeline = key
            self.timelineChanged.emit()
            self.refresh_stats()
            self.save_config()

    @Slot()
    def triggerRefresh(self):
        self.data_service.live_quotas_cache.clear()
        self.data_service._fetching_conn_ids.clear()
        self.check_health()
        self.refresh_stats()

    @Slot()
    def run9routerAction(self):
        run_9router()
        self.check_health()

    @Slot(int, int, int, int, result=list)
    def clampGeometry(self, x, y, w, h):
        """
        Public Slot called from QML after drag release or view change.
        Calculates minimal correction against active screen availableGeometry.
        Returns [clamped_x, clamped_y, is_docked]
        """
        cx, cy, docked, scr = WindowPositionService.clamp_rect_to_screen(
            x, y, w, h, is_docked_notch=self._is_docked_notch
        )
        if docked != self._is_docked_notch:
            self._is_docked_notch = docked
            self.dockedNotchChanged.emit()
        self._target_x = cx
        self._target_y = cy
        self.save_config()
        return [cx, cy, docked]

    @Slot(int, int)
    def updateWindowPosition(self, x, y):
        self._target_x = x
        self._target_y = y
        self.save_config()

    @Slot(bool)
    def setDockedNotch(self, docked):
        if self._is_docked_notch != docked:
            self._is_docked_notch = docked
            self.dockedNotchChanged.emit()
            self.save_config()
