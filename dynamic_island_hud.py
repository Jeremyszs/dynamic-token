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

HEX_BG = '#000000'
HEX_BORDER = '#2C2C2E'
HEX_BORDER_HOVER = '#48484A'
HEX_TEXT_PRIMARY = '#FFFFFF'
HEX_TEXT_SECONDARY = '#98989D'
HEX_TEXT_MUTED = '#636366'
HEX_GREEN = '#30D158'
HEX_BLUE = '#0A84FF'
HEX_ORANGE = '#FF9F0A'
HEX_BADGE_BG = '#151517'

PIL_ISLAND_BG = (0, 0, 0, 255)
PIL_BORDER = (44, 44, 46, 255)
PIL_BORDER_HOVER = (88, 88, 92, 255)

VIEW_SPECS = {
    'min': (320, 42, 21),
    'normal': (520, 136, 26),
    'detailed': (620, 430, 28)
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

        self.load_config()

        w, h, r = VIEW_SPECS[self.current_view]
        self.curr_w = float(w)
        self.curr_h = float(h)
        self.curr_r = float(r)
        self.target_w = float(w)
        self.target_h = float(h)
        self.target_r = float(r)

        # Center X on current saved coordinates or default to primary center
        if self.pos_x is None:
            self.target_x = float((self.screen_w - int(w)) // 2)
            self.target_y = 16.0
        else:
            self.target_x = float(self.pos_x)
            self.target_y = float(self.pos_y)

        self.curr_x = self.target_x
        self.curr_y = self.target_y

        # Keep a steady center anchor so expanding never jumps monitors
        self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)

        # Velocities for spring physics
        self.vel_w = 0.0
        self.vel_h = 0.0
        self.vel_r = 0.0
        self.vel_x = 0.0
        self.vel_y = 0.0

        # Initialize window geometry via native Win32 API
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
            'cost': 0.0,
            'models': {},
            'recent': [],
            'latest_model': '--'
        }
        self.last_max_id = 0

        self.fetch_database_data()

        self.root.after(100, self.apply_win32_styles)

        self.db_thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.db_thread.start()

        self.render()

        self.pulse_frame_idx = 0
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
            # Query the exact native monitor displaying this window
            hmon = win32api.MonitorFromWindow(self.hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            info = win32api.GetMonitorInfo(hmon)
            return info['Work']  # (left, top, right, bottom)
        except Exception:
            return (0, 0, self.screen_w, self.screen_h)

    def set_view(self, view_name):
        if view_name not in VIEW_SPECS:
            return
        self.current_view = view_name
        tw, th, tr = VIEW_SPECS[view_name]

        # Fetch the active monitor's work area directly from Win32
        m_left, m_top, m_right, m_bottom = self.get_current_monitor_workarea()

        # Update anchor center from current coordinates
        self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)

        self.target_w = float(tw)
        self.target_h = float(th)
        self.target_r = float(tr)

        # Expand symmetrically around the anchor center, strictly bounded to current monitor
        self.target_x = max(float(m_left + 10), min(float(m_right - tw - 10), self.anchor_center_x - (tw / 2.0)))
        self.target_y = max(float(m_top + 10), min(float(m_bottom - th - 10), self.curr_y))

        self.is_animating = True
        self.is_dirty = True
        self.save_config()

    def on_mouse_enter(self, event):
        self.is_hovered = True
        if self.current_view == 'min':
            m_left, m_top, m_right, m_bottom = self.get_current_monitor_workarea()
            nw = VIEW_SPECS['min'][0] + 16.0
            nh = VIEW_SPECS['min'][1] + 4.0
            self.target_w = nw
            self.target_h = nh
            # Symmetrical expansion around anchor center without drifting
            self.target_x = max(float(m_left + 10), min(float(m_right - nw - 10), self.anchor_center_x - (nw / 2.0)))
            self.is_animating = True
        self.is_dirty = True

    def on_mouse_leave(self, event):
        self.is_hovered = False
        if self.current_view == 'min':
            m_left, m_top, m_right, m_bottom = self.get_current_monitor_workarea()
            nw = float(VIEW_SPECS['min'][0])
            nh = float(VIEW_SPECS['min'][1])
            self.target_w = nw
            self.target_h = nh
            self.target_x = max(float(m_left + 10), min(float(m_right - nw - 10), self.anchor_center_x - (nw / 2.0)))
            self.is_animating = True
        self.is_dirty = True

    def on_press(self, event):
        # Ground starting coordinates in true Win32 physical window rect
        rect = win32gui.GetWindowRect(self.hwnd)
        self.curr_x = float(rect[0])
        self.curr_y = float(rect[1])
        self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)

        # Use win32api cursor pos to avoid any virtual desktop mapping discrepancies
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
            # Sync true window position after drag
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

            self.stats = {
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

        # User's preferred harmonic spring tuning:
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

            # Render canvas image and items FIRST to avoid rectangular frame flash
            self.canvas.config(width=int(self.curr_w), height=int(self.curr_h))
            self.render()
            self.is_dirty = False

            # Reposition smoothly with native Win32 SetWindowPos (supports negative monitor coords seamlessly)
            user32.SetWindowPos(self.hwnd, 0, int(self.curr_x), int(self.curr_y), int(self.curr_w), int(self.curr_h), SWP_NOZORDER | SWP_NOACTIVATE)

        self.pulse_frame_idx = (self.pulse_frame_idx + 1) % 32
        self.update_antialiased_dot()

        if self.is_dirty:
            self.render()
            self.is_dirty = False

        self.root.after(6, self.tick_loop)

    def render(self):
        w = max(20, int(self.curr_w))
        h = max(20, int(self.curr_h))
        radius = max(8, int(self.curr_r))

        self.hit_zones.clear()

        # Update or create the rounded capsule background WITHOUT wiping it
        border_col = PIL_BORDER_HOVER if self.is_hovered else PIL_BORDER
        img = Image.new('RGBA', (w, h), (1, 1, 1, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=PIL_ISLAND_BG, outline=border_col, width=1)
        self.bg_photo = ImageTk.PhotoImage(img)

        if not self.canvas.find_withtag('bg'):
            self.canvas.create_image(0, 0, anchor='nw', image=self.bg_photo, tags='bg')
        else:
            self.canvas.itemconfig('bg', image=self.bg_photo)

        # Clear only foreground items, leaving the smooth background capsule in place
        for item in self.canvas.find_all():
            if 'bg' not in self.canvas.gettags(item):
                self.canvas.delete(item)

        if self.current_view == 'min':
            self.render_min(w, h)
        elif self.current_view == 'normal':
            self.render_normal(w, h)
        else:
            self.render_detailed(w, h)

        # Ensure background capsule always stays underneath content
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
            font=(FONT_NAME, 9, 'bold')
        )

        tot_tok = self.stats['prompt'] + self.stats['completion']
        tok_str = format_num(tot_tok)
        cost_str = f"${self.stats['cost']:.2f}"
        right_text = f"{tok_str} tok • {cost_str}"

        self.canvas.create_text(
            w - 24, cy, anchor='e',
            text=right_text,
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 9, 'bold')
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

        self.canvas.create_text(
            w - 22, 64, anchor='e',
            text=f"${cost:.2f}  |  {format_num(reqs)} reqs",
            fill=HEX_BLUE,
            font=(FONT_NAME, 12, 'bold')
        )

        recent = self.stats['recent']
        if recent:
            last_call = recent[0]
            t_ago = format_time_ago(last_call[1])
            ticker_txt = f"Last: {t_ago} • {last_call[3]} • +{format_num(last_call[4] + last_call[5])} tok"
        else:
            ticker_txt = "Listening for API calls..."

        self.canvas.create_text(
            22, 104, anchor='w',
            text=ticker_txt,
            fill=HEX_TEXT_SECONDARY,
            font=(FONT_NAME, 9)
        )

        self.canvas.create_text(
            w - 22, 104, anchor='e',
            text='▾ Full',
            fill=HEX_TEXT_MUTED,
            font=(FONT_NAME, 9, 'bold')
        )

    # --- VIEW: DETAILED ---
    def render_detailed(self, w, h):
        self.place_dot(24, 26)

        self.canvas.create_text(
            44, 26, anchor='w',
            text='Token Details & Usage Stats',
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 11, 'bold')
        )

        # Circular Minimize and Shutdown buttons
        self.draw_circle_button(w - 62, 26, r=12, text='—', callback=lambda: self.set_view('min'))
        self.draw_circle_button(w - 32, 26, r=12, text='✕', callback=self.shutdown, bg='#301214', fg='#FF453A', border='#5A1E22')

        self.render_timeline_tabs(24, 60, anchor='w')

        tot_tok = self.stats['prompt'] + self.stats['completion']
        prompt_tok = self.stats['prompt']
        cached_tok = self.stats['cached']
        cost = self.stats['cost']
        reqs = self.stats['requests']
        cache_pct = (cached_tok / prompt_tok * 100) if prompt_tok > 0 else 0.0

        box_x1, box_y1 = 22, 82
        box_w, box_h = w - 44, 72

        card_img = Image.new('RGBA', (box_w, box_h), (1, 1, 1, 0))
        cdraw = ImageDraw.Draw(card_img)
        cdraw.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=16, fill=(21, 21, 23, 255), outline=(44, 44, 46, 255), width=1)
        self.card_photos['stat_card'] = ImageTk.PhotoImage(card_img)
        self.canvas.create_image(box_x1, box_y1, anchor='nw', image=self.card_photos['stat_card'], tags='content')

        col_w = box_w // 4
        self.canvas.create_text(box_x1 + 16, box_y1 + 22, anchor='w', text='TOTAL TOKENS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + 16, box_y1 + 48, anchor='w', text=format_num(tot_tok), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 14, 'bold'))

        self.canvas.create_text(box_x1 + col_w + 16, box_y1 + 22, anchor='w', text='BURN COST', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w + 16, box_y1 + 48, anchor='w', text=f"${cost:.2f}", fill=HEX_GREEN, font=(FONT_NAME, 14, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 2 + 16, box_y1 + 22, anchor='w', text='REQUESTS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 2 + 16, box_y1 + 48, anchor='w', text=format_num(reqs), fill=HEX_BLUE, font=(FONT_NAME, 14, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 3 + 16, box_y1 + 22, anchor='w', text='CACHE RATIO', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 3 + 16, box_y1 + 48, anchor='w', text=f"{cache_pct:.1f}%", fill=HEX_ORANGE, font=(FONT_NAME, 14, 'bold'))

        self.canvas.create_text(24, 178, anchor='w', text='TOP MODELS BREAKDOWN', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        sorted_models = sorted(self.stats['models'].items(), key=lambda item: item[1]['prompt'], reverse=True)[:3]

        bar_y = 202
        for m_name, mdata in sorted_models:
            p_val = mdata['prompt'] + mdata['completion']
            r_val = mdata['requests']
            ratio = min(1.0, p_val / (tot_tok if tot_tok > 0 else 1))

            self.canvas.create_text(24, bar_y, anchor='w', text=m_name, fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9, 'bold'))
            self.canvas.create_text(w - 24, bar_y, anchor='e', text=f"{format_num(p_val)} tok ({r_val} reqs)", fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 9))

            bar_w_max = w - 48
            self.canvas.create_rectangle(24, bar_y + 9, 24 + bar_w_max, bar_y + 14, fill='#1C1C1E', outline='')
            self.canvas.create_rectangle(24, bar_y + 9, 24 + int(bar_w_max * ratio), bar_y + 14, fill=HEX_BLUE, outline='')
            bar_y += 30

        feed_header_y = bar_y + 10
        self.canvas.create_text(24, feed_header_y, anchor='w', text='LIVE API CALL HISTORY', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        feed_y = feed_header_y + 24
        for row in self.stats['recent'][:3]:
            t_ago = format_time_ago(row[1])
            m_tag = row[3]
            toks = row[4] + row[5]
            st = row[7]

            self.canvas.create_rectangle(24, feed_y - 2, 24 + 48, feed_y + 16, fill='#072612' if st == 'ok' else '#3d0a0a', outline='')
            self.canvas.create_text(48, feed_y + 7, anchor='center', text='200 OK' if st == 'ok' else 'ERR', fill=HEX_GREEN if st == 'ok' else '#FF453A', font=(FONT_NAME, 8, 'bold'))

            self.canvas.create_text(82, feed_y + 7, anchor='w', text=f"{m_tag}", fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9))
            self.canvas.create_text(w - 24, feed_y + 7, anchor='e', text=f"+{format_num(toks)} tok • {t_ago}", fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 9))
            feed_y += 26

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
                bg_c = (44, 44, 46, 255) if is_active else (22, 22, 24, 255)
                bd_c = (70, 70, 74, 255) if is_active else (38, 38, 40, 255)
                tdraw.rounded_rectangle([0, 0, tab_w - 1, tab_h - 1], radius=12, fill=bg_c, outline=bd_c, width=1)
                self.card_photos[tab_img_key] = ImageTk.PhotoImage(t_img)

            self.canvas.create_image(bx1, by1, anchor='nw', image=self.card_photos[tab_img_key], tags='content')
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
