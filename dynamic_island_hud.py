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

# Colors & Styling (Pure Pitch Black)
HEX_BG = '#000000'
HEX_BORDER = '#2C2C2E'
HEX_BORDER_HOVER = '#545458'
HEX_TEXT_PRIMARY = '#FFFFFF'
HEX_TEXT_SECONDARY = '#98989D'
HEX_TEXT_MUTED = '#636366'
HEX_GREEN = '#30D158'
HEX_BLUE = '#0A84FF'
HEX_CYAN = '#38BDF8'
HEX_ORANGE = '#FF9F0A'
HEX_PURPLE = '#BF5AF2'
HEX_BADGE_BG = '#151517'

PIL_ISLAND_BG = (0, 0, 0, 255)
PIL_BORDER = (44, 44, 46, 255)
PIL_BORDER_HOVER = (88, 88, 92, 255)
PIL_CARD_BG = (21, 21, 23, 255)
PIL_CARD_BORDER = (44, 44, 46, 255)
PIL_TAB_ACTIVE = (44, 44, 46, 255)
PIL_TAB_INACTIVE = (22, 22, 24, 255)
PIL_RIM_GLOW_RGB = (48, 209, 88)

VIEW_SPECS = {
    'min': (320, 42, 21),
    'normal': (520, 136, 26),
    'detailed': (630, 540, 28)
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
        self.icon_photos = {}

        self.init_antialiased_dots()
        self.init_vector_icons()

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
            'active_account': '--',
            'active_account_full': '--',
            'active_account_reqs': 0,
            'active_account_toks': 0,
            'active_account_priority': 1,
            'account_pool_active': 0,
            'account_pool_total': 0,
            'account_list': [],
            'active_pipeline': 'direct'
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

    def init_vector_icons(self):
        # 1. User Icon (Smooth Antialiased Vector)
        u_size = 14
        u_scale = 4
        u_s = u_size * u_scale
        u_im = Image.new('RGBA', (u_s, u_s), (0, 0, 0, 0))
        u_draw = ImageDraw.Draw(u_im)
        u_cx = u_s / 2
        u_head_r = 3.0 * u_scale
        u_draw.ellipse([u_cx - u_head_r, 1.2 * u_scale, u_cx + u_head_r, 1.2 * u_scale + u_head_r * 2], fill=(152, 152, 157, 255))
        u_draw.pieslice([1.2 * u_scale, 7.8 * u_scale, u_s - 1.2 * u_scale, u_s + 5.5 * u_scale], 180, 360, fill=(152, 152, 157, 255))
        self.icon_photos['user'] = ImageTk.PhotoImage(u_im.resize((u_size, u_size), Image.Resampling.LANCZOS))

        # 2. Lightning Bolt Icon (Vector)
        b_size = 13
        b_scale = 4
        b_s = b_size * b_scale
        b_im = Image.new('RGBA', (b_s, b_s), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(b_im)
        b_pts = [
            (b_s * 0.58, 0),
            (b_s * 0.18, b_s * 0.54),
            (b_s * 0.48, b_s * 0.54),
            (b_s * 0.40, b_s * 0.98),
            (b_s * 0.82, b_s * 0.44),
            (b_s * 0.52, b_s * 0.44),
        ]
        b_draw.polygon(b_pts, fill=(48, 209, 88, 255))
        self.icon_photos['bolt'] = ImageTk.PhotoImage(b_im.resize((b_size, b_size), Image.Resampling.LANCZOS))

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
                    'timeline': self.timeline
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

        # Render layout structure instantly on click
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

            # 1. Latency & Reasoning Tokens
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

            # 2. Full Multi-Account Pool Health Breakdown
            account_list = []
            active_acc_name = '--'
            active_acc_full = '--'
            active_acc_priority = 1
            active_acc_reqs = 0
            active_acc_toks = 0
            active_count = 0
            total_count = 0

            try:
                for r in cur.execute('SELECT id, provider, name, email, priority, isActive, data FROM providerConnections WHERE provider="antigravity" ORDER BY priority ASC').fetchall():
                    total_count += 1
                    is_active = bool(r[5])
                    if is_active:
                        active_count += 1
                    
                    full_email = r[3] or r[2] or '--'
                    short_user = full_email.split('@')[0]
                    astats = today_acc_stats.get(r[0], {})
                    a_reqs = astats.get('requests', 0)
                    a_toks = astats.get('promptTokens', 0)

                    # Check if currently active connection
                    is_current = (latest_conn_id and r[0] == latest_conn_id)
                    if is_current or (active_acc_name == '--' and is_active):
                        active_acc_name = short_user
                        active_acc_full = full_email
                        active_acc_priority = r[4]
                        active_acc_reqs = a_reqs
                        active_acc_toks = a_toks

                    account_list.append({
                        'id': r[0],
                        'short_user': short_user,
                        'full_email': full_email,
                        'priority': r[4],
                        'is_active': is_active,
                        'is_current': is_current,
                        'reqs': a_reqs,
                        'toks': a_toks
                    })
            except Exception:
                pass

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
                'active_account': active_acc_name,
                'active_account_full': active_acc_full,
                'active_account_priority': active_acc_priority,
                'active_account_reqs': active_acc_reqs,
                'active_account_toks': active_acc_toks,
                'account_pool_active': active_count,
                'account_pool_total': total_count,
                'account_list': account_list
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
            # Place small vector lightning bolt next to delta
            self.canvas.create_image(w - 24 - 72, cy - 6, anchor='nw', image=self.icon_photos['bolt'])
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
            self.canvas.create_image(w - 22 - 76, 64 - 6, anchor='nw', image=self.icon_photos['bolt'])
        else:
            norm_right_text = f"${cost:.2f}  |  {format_num(reqs)} reqs"
            norm_color = HEX_BLUE

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

    # --- VIEW: DETAILED ---
    def render_detailed(self, w, h):
        self.place_dot(24, 26)

        # Header Title
        self.canvas.create_text(
            44, 26, anchor='w',
            text='Token Usage & API Call History',
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 11, 'bold')
        )

        # Header Controls: Minimize and Shutdown
        self.draw_circle_button(w - 62, 26, r=12, text='—', callback=lambda: self.set_view('min'))
        self.draw_circle_button(w - 32, 26, r=12, text='X', callback=self.shutdown, bg='#301214', fg='#FF453A', border='#5A1E22')

        # Timeline Selector (Left) + Latency Pill (Right)
        self.render_timeline_tabs(24, 60, anchor='w')

        lat_txt = "-- ms"
        lat_color = HEX_GREEN
        if self.stats.get('latest_latency'):
            tot_ms = self.stats['latest_latency'].get('total', 0)
            ttft_ms = self.stats['latest_latency'].get('ttft', 0)
            if tot_ms > 8000:
                lat_color = HEX_ORANGE
            if tot_ms > 0:
                lat_txt = f"{tot_ms / 1000.0:.2f}s (TTFT {ttft_ms}ms)"

        # Place bolt icon before latency text
        self.canvas.create_image(w - 24 - 110, 60 - 6, anchor='nw', image=self.icon_photos['bolt'])
        self.canvas.create_text(
            w - 24, 60, anchor='e',
            text=lat_txt,
            fill=lat_color,
            font=(FONT_NAME, 8, 'bold')
        )

        # 1. PRIMARY METRICS CARD (5 Columns)
        tot_tok = self.stats['prompt'] + self.stats['completion']
        prompt_tok = self.stats['prompt']
        cached_tok = self.stats['cached']
        cost = self.stats['cost']
        reqs = self.stats['requests']
        reasoning_tok = self.stats['reasoning']
        cache_pct = (cached_tok / prompt_tok * 100) if prompt_tok > 0 else 0.0

        box_x1, box_y1 = 22, 82
        box_w, box_h = w - 44, 70

        card_img = Image.new('RGBA', (box_w, box_h), (1, 1, 1, 0))
        cdraw = ImageDraw.Draw(card_img)
        cdraw.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=16, fill=PIL_CARD_BG, outline=PIL_CARD_BORDER, width=1)
        self.card_photos['stat_card'] = ImageTk.PhotoImage(card_img)
        self.canvas.create_image(box_x1, box_y1, anchor='nw', image=self.card_photos['stat_card'])

        col_w = box_w // 5

        # Col 1: Total Tokens
        self.canvas.create_text(box_x1 + 14, box_y1 + 20, anchor='w', text='TOTAL TOKENS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + 14, box_y1 + 46, anchor='w', text=format_num(tot_tok), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        # Col 2: Cost
        self.canvas.create_text(box_x1 + col_w + 14, box_y1 + 20, anchor='w', text='BURN COST', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w + 14, box_y1 + 46, anchor='w', text=f"${cost:.2f}", fill=HEX_GREEN, font=(FONT_NAME, 13, 'bold'))

        # Col 3: Requests
        self.canvas.create_text(box_x1 + col_w * 2 + 14, box_y1 + 20, anchor='w', text='REQUESTS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 2 + 14, box_y1 + 46, anchor='w', text=format_num(reqs), fill=HEX_BLUE, font=(FONT_NAME, 13, 'bold'))

        # Col 4: Cache Ratio
        self.canvas.create_text(box_x1 + col_w * 3 + 14, box_y1 + 20, anchor='w', text='CACHE RATIO', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 3 + 14, box_y1 + 46, anchor='w', text=f"{cache_pct:.1f}%", fill=HEX_ORANGE, font=(FONT_NAME, 13, 'bold'))

        # Col 5: Thinking Tokens
        self.canvas.create_text(box_x1 + col_w * 4 + 14, box_y1 + 20, anchor='w', text='THINKING', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 4 + 14, box_y1 + 46, anchor='w', text=format_num(reasoning_tok), fill=HEX_PURPLE, font=(FONT_NAME, 13, 'bold'))

        # 2. DEDICATED SECTION: ACCOUNT POOL & FAILOVER HEALTH
        pool_y = 168
        self.canvas.create_text(24, pool_y, anchor='w', text='ACCOUNT POOL & FAILOVER HEALTH', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        # Pool count pill on right: e.g. "5/8 ACTIVE"
        pool_str = f"{self.stats['account_pool_active']}/{self.stats['account_pool_total']} ACTIVE"
        self.canvas.create_text(w - 24, pool_y, anchor='e', text=pool_str, fill=HEX_GREEN, font=(FONT_NAME, 8, 'bold'))

        pool_box_y = pool_y + 12
        pool_box_h = 76

        pool_img = Image.new('RGBA', (box_w, pool_box_h), (1, 1, 1, 0))
        p_draw = ImageDraw.Draw(pool_img)
        p_draw.rounded_rectangle([0, 0, box_w - 1, pool_box_h - 1], radius=16, fill=PIL_CARD_BG, outline=PIL_CARD_BORDER, width=1)
        self.card_photos['pool_card'] = ImageTk.PhotoImage(pool_img)
        self.canvas.create_image(box_x1, pool_box_y, anchor='nw', image=self.card_photos['pool_card'])

        # Left side: Active Account Spotlight
        self.canvas.create_image(box_x1 + 14, pool_box_y + 15, anchor='nw', image=self.icon_photos['user'])
        self.canvas.create_text(
            box_x1 + 34, pool_box_y + 22, anchor='w',
            text=self.stats['active_account_full'],
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 10, 'bold')
        )
        sub_acc = f"Priority {self.stats['active_account_priority']} Active Route • Today: {format_num(self.stats['active_account_toks'])} tok ({self.stats['active_account_reqs']} reqs)"
        self.canvas.create_text(
            box_x1 + 14, pool_box_y + 44, anchor='w',
            text=sub_acc,
            fill=HEX_TEXT_SECONDARY,
            font=(FONT_NAME, 8)
        )

        # Right side: Multi-Account Chain Dots / Badges
        chain_x_start = box_x1 + box_w - 200
        self.canvas.create_text(chain_x_start, pool_box_y + 20, anchor='w', text='FAILOVER POOL', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 7, 'bold'))

        # Draw 8 priority slots horizontally
        slot_x = chain_x_start
        for acc in self.stats.get('account_list', [])[:8]:
            p_num = acc['priority']
            is_on = acc['is_active']
            is_curr = acc['is_current']

            dot_fill = HEX_GREEN if is_curr else (HEX_BLUE if is_on else '#2C2C2E')
            self.canvas.create_rectangle(slot_x, pool_box_y + 36, slot_x + 18, pool_box_y + 54, fill=dot_fill, outline=HEX_BORDER, width=1)
            self.canvas.create_text(slot_x + 9, pool_box_y + 45, text=str(p_num), fill='#000000' if (is_curr or is_on) else HEX_TEXT_MUTED, font=(FONT_NAME, 7, 'bold'))
            slot_x += 24

        # 3. TOP MODELS BREAKDOWN
        models_y = pool_box_y + pool_box_h + 16
        self.canvas.create_text(24, models_y, anchor='w', text='TOP MODELS BREAKDOWN', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        sorted_models = sorted(self.stats['models'].items(), key=lambda item: item[1]['prompt'], reverse=True)[:3]

        bar_y = models_y + 20
        for m_name, mdata in sorted_models:
            p_val = mdata['prompt'] + mdata['completion']
            r_val = mdata['requests']
            ratio = min(1.0, p_val / (tot_tok if tot_tok > 0 else 1))

            self.canvas.create_text(24, bar_y, anchor='w', text=m_name, fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9, 'bold'))
            self.canvas.create_text(w - 24, bar_y, anchor='e', text=f"{format_num(p_val)} tok ({r_val} reqs)", fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 9))

            bar_w_max = w - 48
            self.canvas.create_rectangle(24, bar_y + 9, 24 + bar_w_max, bar_y + 14, fill='#1C1C1E', outline='')
            self.canvas.create_rectangle(24, bar_y + 9, 24 + int(bar_w_max * ratio), bar_y + 14, fill=HEX_BLUE, outline='')
            bar_y += 28

        # 4. LIVE API CALL HISTORY
        feed_header_y = bar_y + 12
        self.canvas.create_text(24, feed_header_y, anchor='w', text='LIVE API CALL HISTORY', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        feed_y = feed_header_y + 22
        for row in self.stats['recent'][:3]:
            t_ago = format_time_ago(row[1])
            m_tag = row[3]
            toks = row[4] + row[5]
            st = row[7]

            self.canvas.create_rectangle(24, feed_y - 2, 24 + 48, feed_y + 16, fill='#072612' if st == 'ok' else '#3d0a0a', outline='')
            self.canvas.create_text(48, feed_y + 7, anchor='center', text='200 OK' if st == 'ok' else 'ERR', fill=HEX_GREEN if st == 'ok' else '#FF453A', font=(FONT_NAME, 8, 'bold'))

            self.canvas.create_text(82, feed_y + 7, anchor='w', text=f"{m_tag}", fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9))
            self.canvas.create_text(w - 24, feed_y + 7, anchor='e', text=f"+{format_num(toks)} tok • {t_ago}", fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 9))
            feed_y += 24

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
                bd_c = (70, 70, 74, 255) if is_active else (38, 38, 40, 255)
                tdraw.rounded_rectangle([0, 0, tab_w - 1, tab_h - 1], radius=12, fill=bg_c, outline=bd_c, width=1)
                self.card_photos[tab_img_key] = ImageTk.PhotoImage(t_img)

            self.canvas.create_image(bx1, by1, anchor='nw', image=self.card_photos[tab_img_key])
            fg = HEX_TEXT_PRIMARY if is_active else HEX_TEXT_SECONDARY
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
