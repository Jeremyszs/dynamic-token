import os
import sys
import math
import time
import json
import sqlite3
import datetime
import threading
import ctypes
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
import win32gui
import win32con
import win32api

# 1. Enable Per-Monitor High-DPI Awareness
user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# 2. Register Apple SF Pro Display Fonts into GDI session
FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
if not os.path.exists(FONT_DIR):
    FONT_DIR = os.path.expandvars(r'%LOCALAPPDATA%\hermes\fonts')

FONT_NAME = 'Segoe UI'
try:
    gdi32 = ctypes.windll.gdi32
    sf_reg = os.path.join(FONT_DIR, 'SF-Pro-Display-Regular.otf')
    sf_bold = os.path.join(FONT_DIR, 'SF-Pro-Display-Bold.otf')
    if os.path.exists(sf_reg):
        gdi32.AddFontResourceExW(sf_reg, 0x10, 0)
    if os.path.exists(sf_bold):
        gdi32.AddFontResourceExW(sf_bold, 0x10, 0)
    FONT_NAME = 'SF Pro Display'
except Exception:
    pass

# --- Configuration & Paths ---
DB_PATH = os.path.expandvars(r'%APPDATA%\9router\db\data.sqlite')
CONFIG_PATH = os.path.expandvars(r'%LOCALAPPDATA%\hermes\dynamic_island_config.json')

COLOR_TRANSPARENT = '#010101'

# Refined Apple Palette
HEX_BG = '#000000'
HEX_BORDER = '#262629'
HEX_BORDER_HOVER = '#444448'
HEX_TEXT_PRIMARY = '#FFFFFF'
HEX_TEXT_SECONDARY = '#A1A1A6'
HEX_TEXT_MUTED = '#58585E'
HEX_GREEN = '#30D158'
HEX_GREEN_MUTED = '#1C3A24'
HEX_ACCENT = '#FFFFFF'
HEX_ORANGE = '#FF9F0A'
HEX_PURPLE = '#BF5AF2'
HEX_BADGE_BG = '#151517'

PIL_ISLAND_BG = (0, 0, 0, 255)
PIL_BORDER = (38, 38, 41, 255)
PIL_BORDER_HOVER = (68, 68, 72, 255)
PIL_CARD_BG = (18, 18, 20, 255)
PIL_CARD_BORDER = (38, 38, 41, 255)
PIL_TAB_ACTIVE = (42, 42, 45, 255)
PIL_TAB_INACTIVE = (18, 18, 20, 255)
PIL_RIM_GLOW_RGB = (48, 209, 88)

# Fixed / Static Window Dimensions (No scrolling, perfectly fits all cards)
VIEW_SPECS = {
    'min': (320, 42, 21),
    'normal': (520, 136, 26),
    'detailed': (630, 530, 28)
}

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

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

def clean_provider_name(p):
    if not p: return '--'
    if p.startswith('openai-compatible-chat'): return 'OpenAI Chat'
    if p.startswith('openai-compatible-responses'): return 'OpenAI Resp'
    if p.startswith('anthropic-compatible'): return 'Anthropic'
    return p.capitalize()

class DynamicIslandHUD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Dynamic Island HUD')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', COLOR_TRANSPARENT)
        self.root.configure(bg=COLOR_TRANSPARENT)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.current_view = 'min'
        self.timeline = 'today'
        self.selected_provider_idx = 0
        self.selected_account_indices = {}
        self.is_hovered = False
        self.last_activity_time = 0
        self.last_delta_tokens = 0
        self.last_delta_time = 0

        self.load_config()

        w, h, r = VIEW_SPECS[self.current_view]
        self.curr_w = float(w)
        self.curr_h = float(h)
        self.curr_r = float(r)
        self.target_w = float(w)
        self.target_h = float(h)
        self.target_r = float(r)

        if self.pos_x is None:
            self.target_x = float((self.screen_w - int(w)) // 2)
            self.target_y = 16.0
        else:
            self.target_x = float(self.pos_x)
            self.target_y = float(self.pos_y)

        self.curr_x = self.target_x
        self.curr_y = self.target_y
        self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)

        # Spring velocities
        self.vel_w = 0.0
        self.vel_h = 0.0
        self.vel_r = 0.0
        self.vel_x = 0.0
        self.vel_y = 0.0

        self.root.update_idletasks()
        self.hwnd = int(self.root.frame(), 16) if hasattr(self.root, 'frame') else self.root.winfo_id()
        user32.SetWindowPos(self.hwnd, 0, int(self.curr_x), int(self.curr_y), int(self.curr_w), int(self.curr_h), SWP_NOZORDER | SWP_NOACTIVATE)

        self.canvas = tk.Canvas(
            self.root,
            width=int(self.curr_w),
            height=int(self.curr_h),
            bg=COLOR_TRANSPARENT,
            highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)

        self.hit_zones = []
        self.bg_photo = None
        self.card_photos = {}

        self.init_antialiased_dots()

        self._drag_start_x = 0
        self._drag_start_y = 0
        self._orig_win_x = self.curr_x
        self._orig_win_y = self.curr_y
        self._dragging = False
        self._was_dragged = False

        self.is_dirty = True
        self.is_animating = False

        self.canvas.bind('<Enter>', self.on_mouse_enter)
        self.canvas.bind('<Leave>', self.on_mouse_leave)
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Button-3>', self.on_right_click)

        self.stats = {
            'requests': 0,
            'prompt': 0,
            'completion': 0,
            'cached': 0,
            'reasoning': 0,
            'cost': 0.0,
            'models': {},
            'recent': [],
            'latest_model': '--',
            'latest_latency': None,
            'providers_data': [],
            'latest_conn_id': None
        }
        self.last_max_id = 0

        self.fetch_database_data()

        self.root.after(100, self.apply_win32_styles)

        self.db_thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.db_thread.start()

        self.render()

        self.pulse_frame_idx = 0
        self.rim_glow_phase = 0.0
        self.last_tick_time = time.perf_counter()
        self.tick_loop()

    def init_antialiased_dots(self):
        self.dot_normal_frames = []
        self.dot_active_frames = []
        size = 28
        scale = 4
        img_size = size * scale
        cx, cy = img_size / 2, img_size / 2

        for i in range(32):
            phase = (i / 32) * 2 * math.pi
            pulse = (math.sin(phase) + 1.0) / 2.0

            im_norm = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
            d_norm = ImageDraw.Draw(im_norm)
            glow_r_norm = (4.5 + 2.0 + pulse * 1.5) * scale
            core_r = 4.2 * scale
            d_norm.ellipse([cx - glow_r_norm, cy - glow_r_norm, cx + glow_r_norm, cy + glow_r_norm], fill=(10, 50, 20, int(130 + pulse * 60)))
            d_norm.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(48, 209, 88, 255))
            self.dot_normal_frames.append(ImageTk.PhotoImage(im_norm.resize((size, size), Image.Resampling.LANCZOS)))

            im_act = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
            d_act = ImageDraw.Draw(im_act)
            glow_r_act = (4.5 + 3.0 + pulse * 4.0) * scale
            d_act.ellipse([cx - glow_r_act, cy - glow_r_act, cx + glow_r_act, cy + glow_r_act], fill=(20, 110, 45, int(150 + pulse * 80)))
            d_act.ellipse([cx - (core_r + 1.5 * scale), cy - (core_r + 1.5 * scale), cx + (core_r + 1.5 * scale), cy + (core_r + 1.5 * scale)], fill=(31, 184, 78, 200))
            d_act.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(52, 230, 98, 255))
            self.dot_active_frames.append(ImageTk.PhotoImage(im_act.resize((size, size), Image.Resampling.LANCZOS)))

    def load_config(self):
        self.pos_x = None
        self.pos_y = None
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    cfg = json.load(f)
                    self.pos_x = cfg.get('x')
                    self.pos_y = cfg.get('y')
                    self.current_view = cfg.get('view', 'min')
                    self.timeline = cfg.get('timeline', 'today')
                    self.selected_provider_idx = cfg.get('provider_idx', 0)
            except Exception:
                pass

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, 'w') as f:
                json.dump({
                    'x': int(self.curr_x),
                    'y': int(self.curr_y),
                    'view': self.current_view,
                    'timeline': self.timeline,
                    'provider_idx': self.selected_provider_idx
                }, f)
        except Exception:
            pass

    def apply_win32_styles(self):
        try:
            ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            ex_style = (ex_style | win32con.WS_EX_TOOLWINDOW) & ~win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, ex_style)
        except Exception:
            pass

    def get_current_monitor_workarea(self):
        try:
            hmon = win32api.MonitorFromWindow(self.hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            info = win32api.GetMonitorInfo(hmon)
            return info['Work']
        except Exception:
            return (0, 0, self.screen_w, self.screen_h)

    def set_view(self, view_name):
        if view_name not in VIEW_SPECS:
            return
        self.current_view = view_name
        tw, th, tr = VIEW_SPECS[view_name]

        m_left, m_top, m_right, m_bottom = self.get_current_monitor_workarea()
        self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)

        self.target_w = float(tw)
        self.target_h = float(th)
        self.target_r = float(tr)

        self.target_x = max(float(m_left + 10), min(float(m_right - tw - 10), self.anchor_center_x - (tw / 2.0)))
        self.target_y = max(float(m_top + 10), min(float(m_bottom - th - 10), self.curr_y))

        self.render(w=int(tw), h=int(th), radius=int(tr))
        self.is_animating = True
        self.is_dirty = False
        self.save_config()

    def on_mouse_enter(self, event):
        self.is_hovered = True
        if self.current_view == 'min' and not self.is_animating:
            m_left, m_top, m_right, m_bottom = self.get_current_monitor_workarea()
            nw = VIEW_SPECS['min'][0] + 16.0
            nh = VIEW_SPECS['min'][1] + 4.0
            self.target_w = nw
            self.target_h = nh
            self.target_x = max(float(m_left + 10), min(float(m_right - nw - 10), self.anchor_center_x - (nw / 2.0)))
            self.is_animating = True
        self.is_dirty = True

    def on_mouse_leave(self, event):
        self.is_hovered = False
        if self.current_view == 'min' and not self.is_animating:
            m_left, m_top, m_right, m_bottom = self.get_current_monitor_workarea()
            nw = float(VIEW_SPECS['min'][0])
            nh = float(VIEW_SPECS['min'][1])
            self.target_w = nw
            self.target_h = nh
            self.target_x = max(float(m_left + 10), min(float(m_right - nw - 10), self.anchor_center_x - (nw / 2.0)))
            self.is_animating = True
        self.is_dirty = True

    def on_press(self, event):
        rect = win32gui.GetWindowRect(self.hwnd)
        self.curr_x = float(rect[0])
        self.curr_y = float(rect[1])
        self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)

        cur_pos = win32api.GetCursorPos()
        self._drag_start_x = cur_pos[0]
        self._drag_start_y = cur_pos[1]
        self._orig_win_x = self.curr_x
        self._orig_win_y = self.curr_y
        self._dragging = False
        self._was_dragged = False

    def on_drag(self, event):
        cur_pos = win32api.GetCursorPos()
        dx = cur_pos[0] - self._drag_start_x
        dy = cur_pos[1] - self._drag_start_y
        if abs(dx) > 3 or abs(dy) > 3:
            self._dragging = True
            self._was_dragged = True
            self.curr_x = self._orig_win_x + dx
            self.curr_y = self._orig_win_y + dy
            self.target_x = self.curr_x
            self.target_y = self.curr_y
            self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)
            user32.SetWindowPos(self.hwnd, 0, int(self.curr_x), int(self.curr_y), int(self.curr_w), int(self.curr_h), SWP_NOZORDER | SWP_NOACTIVATE)

    def on_release(self, event):
        if self._was_dragged:
            rect = win32gui.GetWindowRect(self.hwnd)
            self.curr_x = float(rect[0])
            self.curr_y = float(rect[1])
            self.target_x = self.curr_x
            self.target_y = self.curr_y
            self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)
            self.save_config()
            return

        click_x = event.x
        click_y = event.y
        for (x1, y1, x2, y2, callback) in self.hit_zones:
            if x1 <= click_x <= x2 and y1 <= click_y <= y2:
                callback()
                return

        order = ['min', 'normal', 'detailed']
        next_view = order[(order.index(self.current_view) + 1) % len(order)]
        self.set_view(next_view)

    def on_right_click(self, event):
        if self.current_view == 'min':
            self.set_view('detailed')
        else:
            self.set_view('min')

    def prev_provider(self):
        providers = self.stats.get('providers_data', [])
        if providers:
            self.selected_provider_idx = (self.selected_provider_idx - 1) % len(providers)
            self.save_config()
            self.is_dirty = True

    def next_provider(self):
        providers = self.stats.get('providers_data', [])
        if providers:
            self.selected_provider_idx = (self.selected_provider_idx + 1) % len(providers)
            self.save_config()
            self.is_dirty = True

    def select_account_slot(self, prov_name, slot_idx):
        self.selected_account_indices[prov_name] = slot_idx
        self.is_dirty = True

    def toggle_account_active(self, conn_id, current_status):
        if not os.path.exists(DB_PATH) or not conn_id:
            return
        try:
            con = sqlite3.connect(DB_PATH, timeout=5.0)
            cur = con.cursor()
            new_val = 0 if current_status else 1
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute('UPDATE providerConnections SET isActive = ?, updatedAt = ? WHERE id = ?', (new_val, now_iso, conn_id))
            con.commit()
            con.close()
            self.fetch_database_data()
        except Exception:
            pass

    def toggle_provider_active(self, prov_name, current_any_active):
        if not os.path.exists(DB_PATH) or not prov_name:
            return
        try:
            con = sqlite3.connect(DB_PATH, timeout=5.0)
            cur = con.cursor()
            new_val = 0 if current_any_active else 1
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute('UPDATE providerConnections SET isActive = ?, updatedAt = ? WHERE provider = ?', (new_val, now_iso, prov_name))
            con.commit()
            con.close()
            self.fetch_database_data()
        except Exception:
            pass

    def fetch_database_data(self):
        try:
            if not os.path.exists(DB_PATH):
                return
            con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
            cur = con.cursor()

            row = cur.execute('SELECT MAX(id) FROM usageHistory').fetchone()
            max_id = row[0] if row and row[0] else 0
            if max_id > self.last_max_id:
                if self.last_max_id != 0:
                    self.last_activity_time = time.time()
                    latest_call = cur.execute('SELECT promptTokens, completionTokens FROM usageHistory WHERE id = ?', (max_id,)).fetchone()
                    if latest_call:
                        self.last_delta_tokens = (latest_call[0] or 0) + (latest_call[1] or 0)
                        self.last_delta_time = time.time()
                self.last_max_id = max_id

            today_str = datetime.date.today().isoformat()
            if self.timeline == 'today':
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey = ?', (today_str,)).fetchall()
            elif self.timeline == '7d':
                start_str = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey >= ?', (start_str,)).fetchall()
            elif self.timeline == '30d':
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
            today_acc_stats = {}

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
                    for acc_id, a_stat in d.get('byAccount', {}).items():
                        if acc_id not in today_acc_stats:
                            today_acc_stats[acc_id] = {'requests': 0, 'promptTokens': 0}
                        today_acc_stats[acc_id]['requests'] += a_stat.get('requests', 0)
                        today_acc_stats[acc_id]['promptTokens'] += a_stat.get('promptTokens', 0)
                except Exception:
                    pass

            recent_rows = cur.execute(
                'SELECT id, timestamp, provider, model, promptTokens, completionTokens, cost, status FROM usageHistory ORDER BY id DESC LIMIT 5'
            ).fetchall()

            latest_m = recent_rows[0][3] if recent_rows else '--'

            latest_latency = None
            tot_reasoning = 0
            latest_conn_id = None
            try:
                req_details_row = cur.execute('SELECT data FROM requestDetails ORDER BY id DESC LIMIT 1').fetchone()
                if req_details_row:
                    rd = json.loads(req_details_row[0])
                    latest_latency = rd.get('latency', {})
                    latest_conn_id = rd.get('connectionId')

                time_filter = today_str if self.timeline == 'today' else (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
                for r in cur.execute('SELECT data FROM requestDetails WHERE timestamp >= ?', (time_filter,)).fetchall():
                    try:
                        d = json.loads(r[0])
                        tok = d.get('tokens', {})
                        tot_reasoning += tok.get('reasoning_tokens', 0)
                    except: pass
            except Exception:
                pass

            # Multi-Provider Accounts
            raw_conns = cur.execute('SELECT id, provider, name, email, priority, isActive, data FROM providerConnections ORDER BY provider, priority ASC').fetchall()
            providers_map = {}

            for r in raw_conns:
                raw_prov = r[1]
                if raw_prov not in providers_map:
                    providers_map[raw_prov] = []

                is_active = bool(r[5])
                full_email = r[3] or r[2] or '--'
                short_user = full_email.split('@')[0]
                astats = today_acc_stats.get(r[0], {})
                a_reqs = astats.get('requests', 0)
                a_toks = astats.get('promptTokens', 0)
                is_curr = (latest_conn_id and r[0] == latest_conn_id)

                providers_map[raw_prov].append({
                    'id': r[0],
                    'provider': raw_prov,
                    'short_user': short_user,
                    'full_email': full_email,
                    'priority': r[4],
                    'is_active': is_active,
                    'is_current': is_curr,
                    'reqs': a_reqs,
                    'toks': a_toks
                })

            providers_data = []
            for p_name, accs in providers_map.items():
                active_cnt = sum(1 for a in accs if a['is_active'])
                total_cnt = len(accs)
                total_p_toks = sum(a['toks'] for a in accs)
                total_p_reqs = sum(a['reqs'] for a in accs)
                has_current = any(a['is_current'] for a in accs)

                providers_data.append({
                    'raw_name': p_name,
                    'clean_name': clean_provider_name(p_name),
                    'accounts': accs,
                    'active_count': active_cnt,
                    'total_count': total_cnt,
                    'total_toks': total_p_toks,
                    'total_reqs': total_p_reqs,
                    'has_current': has_current
                })

            providers_data.sort(key=lambda x: (not x['has_current'], -x['total_count'], x['clean_name']))

            self.stats = {
                'requests': reqs,
                'prompt': prompt,
                'completion': comp,
                'cached': cached,
                'reasoning': tot_reasoning,
                'cost': cost,
                'models': by_model,
                'recent': recent_rows,
                'latest_model': latest_m,
                'latest_latency': latest_latency,
                'providers_data': providers_data,
                'latest_conn_id': latest_conn_id
            }
            con.close()
            self.is_dirty = True
        except Exception:
            pass

    def poll_loop(self):
        while True:
            self.fetch_database_data()
            time.sleep(1.0)

    # --- 165Hz Harmonic Spring Loop (stiffness=169, damping=26) ---
    def tick_loop(self):
        now = time.perf_counter()
        dt = min(0.02, max(0.003, now - self.last_tick_time))
        self.last_tick_time = now

        stiffness = 169.0
        damping = 26.0

        if self.is_animating:
            force_w = (self.target_w - self.curr_w) * stiffness - self.vel_w * damping
            force_h = (self.target_h - self.curr_h) * stiffness - self.vel_h * damping
            force_r = (self.target_r - self.curr_r) * stiffness - self.vel_r * damping
            force_x = (self.target_x - self.curr_x) * stiffness - self.vel_x * damping
            force_y = (self.target_y - self.curr_y) * stiffness - self.vel_y * damping

            self.vel_w += force_w * dt
            self.vel_h += force_h * dt
            self.vel_r += force_r * dt
            self.vel_x += force_x * dt
            self.vel_y += force_y * dt

            self.curr_w += self.vel_w * dt
            self.curr_h += self.vel_h * dt
            self.curr_r += self.vel_r * dt
            self.curr_x += self.vel_x * dt
            self.curr_y += self.vel_y * dt

            diff_all = abs(self.target_w - self.curr_w) + abs(self.target_h - self.curr_h) + abs(self.target_x - self.curr_x)
            vel_all = abs(self.vel_w) + abs(self.vel_h) + abs(self.vel_x)

            if diff_all < 0.4 and vel_all < 0.8:
                self.curr_w = self.target_w
                self.curr_h = self.target_h
                self.curr_r = self.target_r
                self.curr_x = self.target_x
                self.curr_y = self.target_y
                self.vel_w = self.vel_h = self.vel_r = self.vel_x = self.vel_y = 0.0
                self.is_animating = False

            self.canvas.config(width=int(self.curr_w), height=int(self.curr_h))
            self.update_morph_layout(int(self.curr_w), int(self.curr_h), int(self.curr_r))
            user32.SetWindowPos(self.hwnd, 0, int(self.curr_x), int(self.curr_y), int(self.curr_w), int(self.curr_h), SWP_NOZORDER | SWP_NOACTIVATE)

        self.pulse_frame_idx = (self.pulse_frame_idx + 1) % 32
        self.rim_glow_phase = (self.rim_glow_phase + 0.12) % (2 * math.pi)
        self.update_antialiased_dot()

        time_since_call = time.time() - self.last_activity_time
        if time_since_call < 2.5:
            self.update_morph_layout(int(self.curr_w), int(self.curr_h), int(self.curr_r))

        if self.last_delta_time != 0 and (time.time() - self.last_delta_time) > 1.8:
            self.last_delta_time = 0
            self.is_dirty = True

        if not self.is_animating and self.is_dirty:
            self.render()
            self.is_dirty = False

        self.root.after(6, self.tick_loop)

    def draw_capsule_image(self, w, h, radius):
        im = Image.new('RGBA', (w, h), (1, 1, 1, 0))
        draw = ImageDraw.Draw(im)

        # 1. Base Pitch Black Fill
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=PIL_ISLAND_BG)

        # 2. Base Perimeter Border
        border_col = PIL_BORDER_HOVER if self.is_hovered else PIL_BORDER
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, outline=border_col, width=1)

        # 3. Specular Perimeter Rim Glow (Siri/AirDrop neon beam)
        time_since_call = time.time() - self.last_activity_time
        if time_since_call < 2.5:
            intensity = max(0.0, 1.0 - (time_since_call / 2.5))
            pulse_brightness = (math.sin(self.rim_glow_phase * 2.0) + 1.0) / 2.0
            alpha = int(220 * intensity * (0.6 + pulse_brightness * 0.4))
            rim_col = (*PIL_RIM_GLOW_RGB, alpha)
            draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, outline=rim_col, width=2)

        return im

    def update_morph_layout(self, w, h, radius):
        img = self.draw_capsule_image(w, h, radius)
        self.bg_photo = ImageTk.PhotoImage(img)

        if not self.canvas.find_withtag('bg'):
            self.canvas.create_image(0, 0, anchor='nw', image=self.bg_photo, tags='bg')
        else:
            self.canvas.itemconfig('bg', image=self.bg_photo)

        cy = h // 2
        if self.current_view == 'min':
            if self.canvas.find_withtag('min_right'):
                self.canvas.coords('min_right', w - 24, cy)
            if self.canvas.find_withtag('min_left'):
                self.canvas.coords('min_left', 36, cy)
            if self.canvas.find_withtag('dot_img'):
                self.canvas.coords('dot_img', 20 - 14, cy - 14)
        elif self.current_view == 'normal':
            if self.canvas.find_withtag('norm_right'):
                self.canvas.coords('norm_right', w - 22, 64)
            if self.canvas.find_withtag('norm_expand'):
                self.canvas.coords('norm_expand', w - 22, 104)

    def render(self, w=None, h=None, radius=None):
        if w is None:
            w = max(20, int(self.curr_w))
        if h is None:
            h = max(20, int(self.curr_h))
        if radius is None:
            radius = max(8, int(self.curr_r))

        self.hit_zones.clear()

        img = self.draw_capsule_image(w, h, radius)
        self.bg_photo = ImageTk.PhotoImage(img)

        if not self.canvas.find_withtag('bg'):
            self.canvas.create_image(0, 0, anchor='nw', image=self.bg_photo, tags='bg')
        else:
            self.canvas.itemconfig('bg', image=self.bg_photo)

        for item in self.canvas.find_all():
            if 'bg' not in self.canvas.gettags(item):
                self.canvas.delete(item)

        if self.current_view == 'min':
            self.render_min(w, h)
        elif self.current_view == 'normal':
            self.render_normal(w, h)
        else:
            self.render_detailed(w, h)

        self.canvas.tag_lower('bg')

    def place_dot(self, cx, cy):
        self.dot_cx = cx
        self.dot_cy = cy
        img = self.dot_normal_frames[0]
        self.canvas.create_image(cx - 14, cy - 14, anchor='nw', image=img, tags='dot_img')

    def update_antialiased_dot(self):
        if not hasattr(self, 'dot_cx'):
            return
        is_active = (time.time() - self.last_activity_time) < 3.0
        frame_list = self.dot_active_frames if is_active else self.dot_normal_frames
        img = frame_list[self.pulse_frame_idx]
        self.canvas.itemconfig('dot_img', image=img)

    # --- VIEW: MINIMUM ---
    def render_min(self, w, h):
        cy = h // 2
        self.place_dot(20, cy)

        raw_m = self.stats['latest_model']
        short_m = raw_m.replace('gemini-', '').replace('flash-', 'f').replace('thinking', 'thk')
        if len(short_m) > 14:
            short_m = short_m[:12] + '..'
        self.canvas.create_text(
            36, cy, anchor='w',
            text=short_m,
            fill=HEX_TEXT_SECONDARY,
            font=(FONT_NAME, 9, 'bold'),
            tags='min_left'
        )

        is_flying_delta = (self.last_delta_time != 0) and ((time.time() - self.last_delta_time) < 1.8)
        if is_flying_delta:
            right_text = f"+{format_num(self.last_delta_tokens)} tok"
            text_color = HEX_GREEN
        else:
            tot_tok = self.stats['prompt'] + self.stats['completion']
            tok_str = format_num(tot_tok)
            cost_str = f"${self.stats['cost']:.2f}"
            right_text = f"{tok_str} tok • {cost_str}"
            text_color = HEX_TEXT_PRIMARY

        self.canvas.create_text(
            w - 24, cy, anchor='e',
            text=right_text,
            fill=text_color,
            font=(FONT_NAME, 9, 'bold'),
            tags='min_right'
        )

    # --- VIEW: NORMAL ---
    def render_normal(self, w, h):
        self.place_dot(22, 24)

        raw_m = self.stats['latest_model']
        self.canvas.create_text(
            40, 24, anchor='w',
            text=raw_m,
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 10, 'bold')
        )

        self.render_timeline_tabs(w - 22, 24, anchor='e')

        tot_tok = self.stats['prompt'] + self.stats['completion']
        reqs = self.stats['requests']
        cost = self.stats['cost']

        self.canvas.create_text(
            22, 64, anchor='w',
            text=f"{format_num(tot_tok)} Tokens",
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 16, 'bold')
        )

        is_flying_delta = (self.last_delta_time != 0) and ((time.time() - self.last_delta_time) < 1.8)
        if is_flying_delta:
            norm_right_text = f"+{format_num(self.last_delta_tokens)} tok"
            norm_color = HEX_GREEN
        else:
            norm_right_text = f"${cost:.2f}  |  {format_num(reqs)} reqs"
            norm_color = HEX_TEXT_PRIMARY

        self.canvas.create_text(
            w - 22, 64, anchor='e',
            text=norm_right_text,
            fill=norm_color,
            font=(FONT_NAME, 12, 'bold'),
            tags='norm_right'
        )

        recent = self.stats['recent']
        if recent:
            last_call = recent[0]
            t_ago = format_time_ago(last_call[1])
            lat_info = ""
            if self.stats.get('latest_latency'):
                tot_ms = self.stats['latest_latency'].get('total', 0)
                if tot_ms > 0:
                    lat_info = f" • {tot_ms / 1000.0:.1f}s"
            ticker_txt = f"Last: {t_ago} • {last_call[3]} • +{format_num(last_call[4] + last_call[5])} tok{lat_info}"
        else:
            ticker_txt = "Listening for API calls..."

        self.canvas.create_text(
            22, 104, anchor='w',
            text=ticker_txt,
            fill=HEX_TEXT_SECONDARY,
            font=(FONT_NAME, 9),
            tags='norm_ticker'
        )

        self.canvas.create_text(
            w - 22, 104, anchor='e',
            text='Full',
            fill=HEX_TEXT_MUTED,
            font=(FONT_NAME, 9, 'bold'),
            tags='norm_expand'
        )

    # --- VIEW: DETAILED (Clean, Non-scrollable, Perfect Apple Padding & Corners) ---
    def render_detailed(self, w, h):
        box_x1 = 22
        box_w = w - 44

        # 1. Header (y=26)
        self.place_dot(24, 26)

        self.canvas.create_text(
            44, 26, anchor='w',
            text='Token Usage & API Call History',
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 11, 'bold')
        )

        # Header Controls: Minimize and Shutdown
        self.draw_circle_button(w - 62, 26, r=12, text='—', callback=lambda: self.set_view('min'))
        self.draw_circle_button(w - 32, 26, r=12, text='X', callback=self.shutdown, bg='#241416', fg='#FF453A', border='#4A1E22')

        # Row 2 (y=60): Timeline Tabs & Latency Metric
        self.render_timeline_tabs(24, 60, anchor='w')

        lat_txt = "-- ms"
        lat_color = HEX_TEXT_SECONDARY
        if self.stats.get('latest_latency'):
            tot_ms = self.stats['latest_latency'].get('total', 0)
            ttft_ms = self.stats['latest_latency'].get('ttft', 0)
            if tot_ms > 8000:
                lat_color = HEX_ORANGE
            elif tot_ms > 0:
                lat_color = HEX_GREEN
            if tot_ms > 0:
                lat_txt = f"{tot_ms / 1000.0:.2f}s (TTFT {ttft_ms}ms)"

        self.canvas.create_text(
            w - 24, 60, anchor='e',
            text=lat_txt,
            fill=lat_color,
            font=(FONT_NAME, 8, 'bold')
        )

        # 2. PRIMARY METRICS CARD (y=84, h=70)
        tot_tok = self.stats['prompt'] + self.stats['completion']
        prompt_tok = self.stats['prompt']
        cached_tok = self.stats['cached']
        cost = self.stats['cost']
        reqs = self.stats['requests']
        reasoning_tok = self.stats['reasoning']
        cache_pct = (cached_tok / prompt_tok * 100) if prompt_tok > 0 else 0.0

        box_y1 = 84
        box_h = 70

        self.draw_rounded_card('stat_card', box_x1, box_y1, box_w, box_h, radius=16)

        col_w = box_w // 5
        self.canvas.create_text(box_x1 + 14, box_y1 + 20, anchor='w', text='TOTAL TOKENS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + 14, box_y1 + 46, anchor='w', text=format_num(tot_tok), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w + 14, box_y1 + 20, anchor='w', text='BURN COST', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w + 14, box_y1 + 46, anchor='w', text=f"${cost:.2f}", fill=HEX_GREEN, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 2 + 14, box_y1 + 20, anchor='w', text='REQUESTS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 2 + 14, box_y1 + 46, anchor='w', text=format_num(reqs), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 3 + 14, box_y1 + 20, anchor='w', text='CACHE RATIO', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 3 + 14, box_y1 + 46, anchor='w', text=f"{cache_pct:.1f}%", fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 4 + 14, box_y1 + 20, anchor='w', text='THINKING', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 4 + 14, box_y1 + 46, anchor='w', text=format_num(reasoning_tok), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        # 3. DEDICATED SECTION: ACCOUNT MANAGER (y=176, h=106)
        pool_header_y = 176
        self.canvas.create_text(24, pool_header_y, anchor='w', text='ACCOUNT MANAGER', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        providers = self.stats.get('providers_data', [])
        num_providers = len(providers)
        if num_providers > 0:
            p_idx = self.selected_provider_idx % num_providers
            curr_prov = providers[p_idx]
        else:
            curr_prov = {'raw_name': '', 'clean_name': 'None', 'accounts': [], 'active_count': 0, 'total_count': 0, 'total_toks': 0, 'total_reqs': 0}

        # Carousel Provider Navigation: [ ‹ ] [ Provider Name ] [ › ]
        car_x = w - 24
        self.draw_circle_button(car_x - 12, pool_header_y, r=10, text='›', callback=self.next_provider)
        prov_label = f"{curr_prov['clean_name']} ({p_idx + 1}/{num_providers})"
        self.canvas.create_text(car_x - 32, pool_header_y, anchor='e', text=prov_label, fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 8, 'bold'))
        prov_lbl_len = len(prov_label) * 6 + 18
        self.draw_circle_button(car_x - 32 - prov_lbl_len, pool_header_y, r=10, text='‹', callback=self.prev_provider)

        # Provider Level Action Button: [ Turn Off All ] / [ Turn On All ] with rounded radius=8
        any_active_in_prov = (curr_prov.get('active_count', 0) > 0)
        p_action_txt = "Disable All" if any_active_in_prov else "Enable All"
        p_btn_w = 72
        p_btn_x2 = car_x - 32 - prov_lbl_len - 14
        p_btn_x1 = p_btn_x2 - p_btn_w
        self.draw_pill_button_styled(p_btn_x1, pool_header_y - 10, p_btn_x2, pool_header_y + 10, p_action_txt,
                                    callback=lambda: self.toggle_provider_active(curr_prov.get('raw_name'), any_active_in_prov),
                                    fill='#1C1C1F', fg=HEX_TEXT_SECONDARY if any_active_in_prov else HEX_GREEN, radius=8)

        # Account Manager Card Container
        pool_box_y = pool_header_y + 16
        pool_box_h = 106

        self.draw_rounded_card('pool_card', box_x1, pool_box_y, box_w, pool_box_h, radius=16)

        accs = curr_prov.get('accounts', [])
        prov_raw = curr_prov.get('raw_name', '')

        current_active_idx = 0
        for i, a in enumerate(accs):
            if a.get('is_current'):
                current_active_idx = i
                break

        sel_acc_idx = self.selected_account_indices.get(prov_raw, current_active_idx)
        if sel_acc_idx >= len(accs) and accs:
            sel_acc_idx = 0
            self.selected_account_indices[prov_raw] = 0

        displayed_acc = accs[sel_acc_idx] if (accs and sel_acc_idx < len(accs)) else None

        if displayed_acc:
            acc_name = displayed_acc.get('full_email') or displayed_acc.get('name') or '--'
            is_curr = displayed_acc.get('is_current', False)
            is_on = displayed_acc.get('is_active', False)

            status_text = "Active Route" if is_curr else ("Standby Ready" if is_on else "Exhausted / Disabled")
            status_color = HEX_GREEN if is_curr else (HEX_TEXT_PRIMARY if is_on else HEX_TEXT_MUTED)

            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 20, anchor='w',
                text=acc_name,
                fill=HEX_TEXT_PRIMARY,
                font=(FONT_NAME, 11, 'bold')
            )

            quota_sub = f"Priority {displayed_acc.get('priority', 1)} • {status_text} • Today: {format_num(displayed_acc.get('toks', 0))} tok ({displayed_acc.get('reqs', 0)} reqs)"
            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 42, anchor='w',
                text=quota_sub,
                fill=status_color,
                font=(FONT_NAME, 8)
            )

            tot_p_sub = f"Provider Total: {curr_prov['active_count']}/{curr_prov['total_count']} Active • {format_num(curr_prov['total_toks'])} tok burned today"
            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 64, anchor='w',
                text=tot_p_sub,
                fill=HEX_TEXT_MUTED,
                font=(FONT_NAME, 8)
            )

            # Account Level Action Button with Clean Border Radius (radius=9)
            acc_action_txt = "Deactivate Account" if is_on else "Activate Account"
            acc_btn_color = '#381618' if is_on else '#122E1A'
            acc_btn_border = '#662228' if is_on else '#1E5E2A'
            acc_text_color = '#FF6961' if is_on else HEX_GREEN

            ab_w = 124
            ab_h = 20
            ab_x1 = box_x1 + 16
            ab_y1 = pool_box_y + 76
            ab_x2 = ab_x1 + ab_w
            ab_y2 = ab_y1 + ab_h

            self.draw_pill_button_styled(ab_x1, ab_y1, ab_x2, ab_y2, acc_action_txt,
                                        callback=lambda cid=displayed_acc.get('id'), st=is_on: self.toggle_account_active(cid, st),
                                        fill=acc_btn_color, fg=acc_text_color, border=acc_btn_border, radius=9)
        else:
            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 47, anchor='w',
                text="No accounts registered for this provider",
                fill=HEX_TEXT_MUTED,
                font=(FONT_NAME, 9)
            )

        # Right Column: Interactive Account Slot Selector (Clickable 1..N) with rounded pills
        chain_w = 210
        chain_x_start = box_x1 + box_w - chain_w
        self.canvas.create_text(chain_x_start, pool_box_y + 20, anchor='w', text='SELECT ACCOUNT', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 7, 'bold'))

        slot_x = chain_x_start
        for i, acc in enumerate(accs[:8]):
            p_num = acc.get('priority', i + 1)
            is_on = acc.get('is_active', False)
            is_curr = acc.get('is_current', False)
            is_selected = (i == sel_acc_idx)

            if is_curr:
                btn_fill = HEX_GREEN_MUTED
                btn_fg = HEX_GREEN
                btn_border = HEX_GREEN
            elif is_on:
                btn_fill = '#232326'
                btn_fg = HEX_TEXT_PRIMARY
                btn_border = '#3C3C40'
            else:
                btn_fill = '#141416'
                btn_fg = HEX_TEXT_MUTED
                btn_border = '#242426'

            if is_selected:
                btn_border = '#FFFFFF'

            bx1, by1 = slot_x, pool_box_y + 36
            bx2, by2 = slot_x + 22, pool_box_y + 60

            self.draw_pill_button_styled(bx1, by1, bx2, by2, str(p_num),
                                        callback=lambda idx=i, pr=prov_raw: self.select_account_slot(pr, idx),
                                        fill=btn_fill, fg=btn_fg, border=btn_border, radius=6)
            slot_x += 26

        # 4. TOP MODELS BREAKDOWN (Bold section title, 8px gap above bar)
        models_header_y = pool_box_y + pool_box_h + 20
        self.canvas.create_text(24, models_header_y, anchor='w', text='TOP MODELS BREAKDOWN', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        sorted_models = sorted(self.stats['models'].items(), key=lambda item: item[1]['prompt'], reverse=True)[:3]

        bar_y = models_header_y + 18
        for m_name, mdata in sorted_models:
            p_val = mdata['prompt'] + mdata['completion']
            r_val = mdata['requests']
            ratio = min(1.0, p_val / (tot_tok if tot_tok > 0 else 1))

            self.canvas.create_text(24, bar_y, anchor='w', text=m_name, fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9))
            self.canvas.create_text(w - 24, bar_y, anchor='e', text=f"{format_num(p_val)} tok ({r_val} reqs)", fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 8))

            bar_w_max = w - 48
            # 8px vertical gap between model label baseline and track bar
            self.canvas.create_rectangle(24, bar_y + 14, 24 + bar_w_max, bar_y + 18, fill='#1C1C1E', outline='')
            self.canvas.create_rectangle(24, bar_y + 14, 24 + int(bar_w_max * ratio), bar_y + 18, fill='#E5E5EA', outline='')
            bar_y += 32

        # 5. LIVE API CALL HISTORY (Bold section title)
        feed_header_y = bar_y + 12
        self.canvas.create_text(24, feed_header_y, anchor='w', text='LIVE API CALL HISTORY', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        feed_y = feed_header_y + 20
        for row in self.stats['recent'][:3]:
            t_ago = format_time_ago(row[1])
            m_tag = row[3]
            toks = row[4] + row[5]
            st = row[7]

            self.canvas.create_rectangle(24, feed_y - 2, 24 + 48, feed_y + 16, fill='#072612' if st == 'ok' else '#260B0D', outline='')
            self.canvas.create_text(48, feed_y + 7, anchor='center', text='200 OK' if st == 'ok' else 'ERR', fill=HEX_GREEN if st == 'ok' else '#FF453A', font=(FONT_NAME, 8, 'bold'))

            self.canvas.create_text(82, feed_y + 7, anchor='w', text=f"{m_tag}", fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9))
            self.canvas.create_text(w - 24, feed_y + 7, anchor='e', text=f"+{format_num(toks)} tok • {t_ago}", fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 9))
            feed_y += 24

    # --- UI Helpers & Rounded Card Rasterizers ---
    def draw_rounded_card(self, cache_key, x, y, width, height, radius=16):
        card_key = f"{cache_key}_{width}_{height}_{radius}"
        if card_key not in self.card_photos:
            card_img = Image.new('RGBA', (width, height), (1, 1, 1, 0))
            cdraw = ImageDraw.Draw(card_img)
            cdraw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=PIL_CARD_BG, outline=PIL_CARD_BORDER, width=1)
            self.card_photos[card_key] = ImageTk.PhotoImage(card_img)
        self.canvas.create_image(x, y, anchor='nw', image=self.card_photos[card_key])

    def draw_pill_button_styled(self, x1, y1, x2, y2, text, callback, fill='#1C1C1F', fg=HEX_TEXT_PRIMARY, border=HEX_BORDER, radius=8):
        bw = max(4, x2 - x1)
        bh = max(4, y2 - y1)
        key = f"pill_{bw}_{bh}_{fill}_{border}_{radius}"
        if key not in self.card_photos:
            im = Image.new('RGBA', (bw, bh), (1, 1, 1, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=radius, fill=fill, outline=border, width=1)
            self.card_photos[key] = ImageTk.PhotoImage(im)

        self.canvas.create_image(x1, y1, anchor='nw', image=self.card_photos[key])
        self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=text, fill=fg, font=(FONT_NAME, 7, 'bold'))
        self.hit_zones.append((x1, y1, x2, y2, callback))

    def render_timeline_tabs(self, x, y, anchor='e'):
        tabs = [('today', 'Today'), ('7d', '7D'), ('30d', '30D'), ('all', 'All')]
        tab_w = 52
        tab_h = 24
        total_w = len(tabs) * (tab_w + 6)

        start_x = x - total_w if anchor == 'e' else x

        for i, (key, label) in enumerate(tabs):
            bx1 = start_x + i * (tab_w + 6)
            by1 = y - tab_h // 2
            bx2 = bx1 + tab_w
            by2 = by1 + tab_h

            is_active = (self.timeline == key)
            tab_img_key = f"tab_{key}_{is_active}"
            if tab_img_key not in self.card_photos:
                t_img = Image.new('RGBA', (tab_w, tab_h), (1, 1, 1, 0))
                tdraw = ImageDraw.Draw(t_img)
                bg_c = PIL_TAB_ACTIVE if is_active else PIL_TAB_INACTIVE
                bd_c = (60, 60, 64, 255) if is_active else (32, 32, 35, 255)
                tdraw.rounded_rectangle([0, 0, tab_w - 1, tab_h - 1], radius=12, fill=bg_c, outline=bd_c, width=1)
                self.card_photos[tab_img_key] = ImageTk.PhotoImage(t_img)

            self.canvas.create_image(bx1, by1, anchor='nw', image=self.card_photos[tab_img_key])
            fg = HEX_TEXT_PRIMARY if is_active else HEX_TEXT_MUTED
            self.canvas.create_text((bx1 + bx2) // 2, (by1 + by2) // 2, text=label, fill=fg, font=(FONT_NAME, 8, 'bold'))

            def make_handler(k):
                return lambda: self.switch_timeline(k)

            self.hit_zones.append((bx1, by1, bx2, by2, make_handler(key)))

    def draw_circle_button(self, cx, cy, r, text, callback, bg='#1C1C1E', fg=HEX_TEXT_PRIMARY, border=HEX_BORDER):
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=bg, outline=border, width=1)
        self.canvas.create_text(cx, cy, text=text, fill=fg, font=(FONT_NAME, 8, 'bold'))
        self.hit_zones.append((cx - r, cy - r, cx + r, cy + r, callback))

    def shutdown(self):
        self.save_config()
        self.root.destroy()
        sys.exit(0)

    def switch_timeline(self, key):
        self.timeline = key
        self.save_config()
        self.fetch_database_data()
        self.is_dirty = True

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    hud = DynamicIslandHUD()
    hud.run()
