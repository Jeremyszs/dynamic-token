import os
import json
import time
import datetime
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
from PySide6.QtGui import QGuiApplication
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
    'detailed': (660, 540, 28)
}

class HUDController(QObject):
    # Signals
    viewChanged = Signal()
    timelineChanged = Signal()
    statsChanged = Signal()
    routerStatusChanged = Signal()
    splitActiveChanged = Signal()
    dockedNotchChanged = Signal()
    selectedProviderChanged = Signal()
    selectedAccountChanged = Signal()
    hoveredChanged = Signal()
    requestWindowResize = Signal(int, int, int) # w, h, radius
    requestWindowMove = Signal(int, int)       # x, y

    def __init__(self):
        super().__init__()
        self.scaling = ScalingService(self)
        self.data_service = DataService(on_data_updated=self._on_background_data_ready)
        
        self._current_view = 'min'
        self._timeline = 'today'
        self._selected_provider_idx = 0
        self._selected_account_indices = {}
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
            self.viewChanged.emit()

    @Property(QObject, constant=True)
    def scaler(self):
        return self.scaling

    @Property(int, notify=viewChanged)
    def targetWidth(self):
        pw, _, _ = TKINTER_PHYSICAL_SPECS[self._current_view]
        # Stretch min view when hovered with cursor (320px -> 350px physical)
        if self._current_view == 'min' and self._is_hovered:
            pw = 350
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
                    self._selected_provider_idx = cfg.get('provider_idx', 0)
                    self.data_service.custom_quotas = cfg.get('quotas', {})
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
                    'provider_idx': self._selected_provider_idx,
                    'quotas': self.data_service.custom_quotas,
                    'docked_notch': self._is_docked_notch
                }, f)
        except Exception:
            pass

    def _on_background_data_ready(self):
        self.statsChanged.emit()
        self.selectedAccountChanged.emit()
        self.selectedProviderChanged.emit()

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
            self.selectedAccountChanged.emit()
            self.selectedProviderChanged.emit()

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

    # Provider and Account Manager properties
    @Property('QVariantList', notify=statsChanged)
    def providersList(self):
        return self.stats.get('providers_data', [])

    @Property(int, notify=selectedProviderChanged)
    def selectedProviderIndex(self):
        return self._selected_provider_idx

    @Property('QVariantMap', notify=selectedProviderChanged)
    def currentProvider(self):
        provs = self.stats.get('providers_data', [])
        if provs:
            idx = self._selected_provider_idx % len(provs)
            return provs[idx]
        return {'raw_name': '', 'clean_name': 'None', 'accounts': [], 'active_count': 0, 'total_count': 0, 'total_toks': 0, 'total_reqs': 0}

    @Property('QVariantMap', notify=selectedAccountChanged)
    def currentAccount(self):
        prov = self.currentProvider
        accs = prov.get('accounts', [])
        raw_name = prov.get('raw_name', '')
        if not accs:
            return {}

        current_active_idx = 0
        for i, a in enumerate(accs):
            if a.get('is_current'):
                current_active_idx = i
                break
        sel_idx = self._selected_account_indices.get(raw_name, current_active_idx)
        if sel_idx >= len(accs):
            sel_idx = 0
        
        acc = dict(accs[sel_idx])
        # Enrich with live quota & limit
        cid = acc.get('id')
        live_data = self.data_service.fetch_live_quota(cid, self._is_9router_running)
        live_pct = None
        live_reset_at = None
        if live_data and 'quotas' in live_data:
            q_dict = live_data['quotas']
            latest_m = self.stats.get('latest_model', '')
            best_q = q_dict.get(latest_m) or q_dict.get('gemini-3.8-flash-high') or (next(iter(q_dict.values())) if q_dict else None)
            if best_q and 'remainingPercentage' in best_q:
                live_pct = max(0.0, min(100.0, 100.0 - float(best_q['remainingPercentage'])))
                live_reset_at = best_q.get('resetAt')

        if not live_reset_at and acc.get('reset_at'):
            live_reset_at = acc['reset_at']
        if not live_reset_at:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            live_reset_at = (now_utc + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        acc_limit = self.data_service.get_account_quota_limit(raw_name, acc.get('full_email', ''))
        if live_pct is not None:
            pct = live_pct
            used = int(acc_limit * (pct / 100.0))
        else:
            used = acc.get('quota_toks', 0)
            pct = (used / acc_limit * 100.0) if acc_limit > 0 else 0.0

        acc['used_tokens'] = used
        acc['limit_tokens'] = acc_limit
        acc['used_str'] = format_num(used)
        acc['limit_str'] = format_num(acc_limit)
        acc['used_pct'] = pct
        acc['used_pct_str'] = f"{pct:.1f}%"
        acc['reset_time_left'] = format_time_left(live_reset_at) or ""
        acc['slot_index'] = sel_idx
        return acc

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

    @Slot()
    def nextProvider(self):
        provs = self.stats.get('providers_data', [])
        if provs:
            self._selected_provider_idx = (self._selected_provider_idx + 1) % len(provs)
            self.selectedProviderChanged.emit()
            self.selectedAccountChanged.emit()
            self.save_config()

    @Slot()
    def prevProvider(self):
        provs = self.stats.get('providers_data', [])
        if provs:
            self._selected_provider_idx = (self._selected_provider_idx - 1) % len(provs)
            self.selectedProviderChanged.emit()
            self.selectedAccountChanged.emit()
            self.save_config()

    @Slot(str, int)
    def selectAccountSlot(self, prov_name, slot_idx):
        self._selected_account_indices[prov_name] = slot_idx
        self.selectedAccountChanged.emit()

    @Slot(str, bool)
    def toggleAccountActive(self, conn_id, current_status):
        self.data_service.toggle_account_active(conn_id, current_status)
        self.refresh_stats()
        self.selectedAccountChanged.emit()

    @Slot(str, bool)
    def toggleProviderActive(self, prov_name, current_any_active):
        self.data_service.toggle_provider_active(prov_name, current_any_active)
        self.refresh_stats()
        self.selectedProviderChanged.emit()
        self.selectedAccountChanged.emit()

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
