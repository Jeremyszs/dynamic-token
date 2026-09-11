import os
import sys
import math
import time
import json
import sqlite3
import datetime
import threading
import ctypes
from ctypes import wintypes
import urllib.request
import webbrowser
import subprocess
import winreg
import tkinter as tk
from tkinter import font as tkfont
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

COLOR_TRANSPARENT = '#010203'
PIL_TRANSPARENT_RGB = (1, 2, 3)

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
PIL_RIM_GLOW_ERROR_RGB = (255, 69, 58)
RASTER_SCALE = 2

# Fixed / Static Window Dimensions (No scrolling, perfectly fits all cards)
# Detailed view width widened to 660px for extra breathing room across long email handles and model names
VIEW_SPECS = {
    'min': (320, 42, 21),
    'normal': (520, 136, 26),
    'detailed': (660, 540, 28)
}

SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_NOCOPYBITS = 0x0100
SWP_FLAGS = SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOCOPYBITS
SWP_MOVE_FLAGS = SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOCOPYBITS

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

def format_time_left(reset_at_str):
    if not reset_at_str:
        return None
    try:
        cleaned = reset_at_str.replace('Z', '+00:00')
        dt = datetime.datetime.fromisoformat(cleaned)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff_s = int((dt - now).total_seconds())
        if diff_s <= 0:
            return 'Resetting...'
        days = diff_s // 86400
        hours = (diff_s % 86400) // 3600
        mins = (diff_s % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {mins}m"
        if mins > 0:
            return f"{mins}m"
        return f"{diff_s}s"
    except Exception:
        return None

def clean_provider_name(p):
    if not p: return '--'
    if p.startswith('openai-compatible-chat'): return 'OpenAI Chat'
    if p.startswith('openai-compatible-responses'): return 'OpenAI Resp'
    if p.startswith('anthropic-compatible'): return 'Anthropic'
    return p.capitalize()

def clean_model_display_name(m):
    if not m: return '--'
    # Strip verbose provider prefixes and UUIDs (e.g. openai-compatible-responses-uuid/deepseek-v4 -> deepseek-v4)
    if '/' in m:
        parts = m.split('/')
        if len(parts[-1]) >= 3:
            m = parts[-1]
    return m

def truncate_text_to_pixel_width(font_obj, text, max_px):
    if not text or max_px <= 10:
        return ""
    w = font_obj.measure(text)
    if w <= max_px:
        return text
    # Binary search or trim from end with ellipsis
    ell = ".."
    ell_w = font_obj.measure(ell)
    avail = max(0, max_px - ell_w)
    low = 0
    high = len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        sub = text[:mid]
        if font_obj.measure(sub) <= avail:
            best = sub
            low = mid + 1
        else:
            high = mid - 1
    return best + ell

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
        self.last_activity_is_error = False
        self.last_delta_tokens = 0
        self.last_delta_time = 0

        # Quota limit definitions (tokens per account per day).
        # Antigravity/Gemini pro quotas default to 200M/acc; OpenAI/Codex to 100M/acc; other keys to 50M/acc
        self.default_account_quotas = {
            'antigravity': 200_000_000,
            'codex': 150_000_000,
            'gemini': 200_000_000,
            'kilocode': 100_000_000,
            'default': 100_000_000
        }
        self.custom_quotas = {}

        self.load_config()

        # Cached Tkinter font objects for precise pixel-width measurement
        self.font_cache = {
            ('f', 7, 'bold'): tkfont.Font(family=FONT_NAME, size=7, weight='bold'),
            ('f', 8, 'normal'): tkfont.Font(family=FONT_NAME, size=8),
            ('f', 8, 'bold'): tkfont.Font(family=FONT_NAME, size=8, weight='bold'),
            ('f', 9, 'normal'): tkfont.Font(family=FONT_NAME, size=9),
            ('f', 9, 'bold'): tkfont.Font(family=FONT_NAME, size=9, weight='bold'),
            ('f', 10, 'bold'): tkfont.Font(family=FONT_NAME, size=10, weight='bold'),
            ('f', 11, 'bold'): tkfont.Font(family=FONT_NAME, size=11, weight='bold'),
        }

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

        # Multi-monitor bounds clamp on startup so expanded detailed view never bleeds off-screen
        try:
            hmon = win32api.MonitorFromPoint((int(self.target_x), int(self.target_y)), win32con.MONITOR_DEFAULTTONEAREST)
            mon_info = win32api.GetMonitorInfo(hmon)['Work']
            self.target_x = max(float(mon_info[0] + 10), min(float(mon_info[2] - w - 10), self.target_x))
            self.target_y = max(float(mon_info[1] + 10), min(float(mon_info[3] - h - 10), self.target_y))
        except Exception:
            pass

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
        user32.SetWindowPos(self.hwnd, 0, int(self.curr_x), int(self.curr_y), int(self.curr_w), int(self.curr_h), SWP_FLAGS)

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
        self._capsule_cache = {}
        self._capsule_photo_cache = {}
        self._last_morph_paint = 0.0
        self._morph_photo_key = None
        self._morph_region_key = None

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
        self.last_rd_rowid = 0
        self.latest_tps = None
        self.is_9router_running = False
        self.live_quotas_cache = {}
        self._fetching_conn_ids = set()

        # Dynamic Shape Transformations (Notch Docking & Split Island)
        self.is_docked_notch = False
        self.notch_morph_progress = 0.0  # 0.0 = full floating pill, 1.0 = hardware notch flat top
        self.is_split_active = False
        self.split_morph_progress = 0.0  # 0.0 = continuous capsule, 1.0 = detached bubble
        self.vel_split = 0.0
        self.target_split = 0.0
        self.split_bubble_w = 46.0
        self.split_bubble_gap = 10.0
        self._last_rgn_state = None
        self._last_live_quota_fetch = 0.0

        self.check_startup_registration()
        self.fetch_database_data()
        self.check_9router_health()

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
        self.dot_error_frames = []
        size = 28
        scale = 4
        img_size = size * scale
        cx, cy = img_size / 2, img_size / 2

        for i in range(32):
            phase = (i / 32) * 2 * math.pi
            pulse = (math.sin(phase) + 1.0) / 2.0

            # Normal resting green
            im_norm = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
            d_norm = ImageDraw.Draw(im_norm)
            glow_r_norm = (4.5 + 2.0 + pulse * 1.5) * scale
            core_r = 4.2 * scale
            d_norm.ellipse([cx - glow_r_norm, cy - glow_r_norm, cx + glow_r_norm, cy + glow_r_norm], fill=(10, 50, 20, int(130 + pulse * 60)))
            d_norm.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(48, 209, 88, 255))
            self.dot_normal_frames.append(ImageTk.PhotoImage(im_norm.resize((size, size), Image.Resampling.LANCZOS)))

            # Active live call green
            im_act = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
            d_act = ImageDraw.Draw(im_act)
            glow_r_act = (4.5 + 3.0 + pulse * 4.0) * scale
            d_act.ellipse([cx - glow_r_act, cy - glow_r_act, cx + glow_r_act, cy + glow_r_act], fill=(20, 110, 45, int(150 + pulse * 80)))
            d_act.ellipse([cx - (core_r + 1.5 * scale), cy - (core_r + 1.5 * scale), cx + (core_r + 1.5 * scale), cy + (core_r + 1.5 * scale)], fill=(31, 184, 78, 200))
            d_act.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(52, 230, 98, 255))
            self.dot_active_frames.append(ImageTk.PhotoImage(im_act.resize((size, size), Image.Resampling.LANCZOS)))

            # Error / 429 Red alert
            im_err = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
            d_err = ImageDraw.Draw(im_err)
            glow_r_err = (4.5 + 3.5 + pulse * 4.5) * scale
            d_err.ellipse([cx - glow_r_err, cy - glow_r_err, cx + glow_r_err, cy + glow_r_err], fill=(110, 20, 25, int(160 + pulse * 80)))
            d_err.ellipse([cx - (core_r + 1.5 * scale), cy - (core_r + 1.5 * scale), cx + (core_r + 1.5 * scale), cy + (core_r + 1.5 * scale)], fill=(184, 35, 45, 200))
            d_err.ellipse([cx - core_r, cy - core_r, cx + core_r, cy + core_r], fill=(255, 69, 58, 255))
            self.dot_error_frames.append(ImageTk.PhotoImage(im_err.resize((size, size), Image.Resampling.LANCZOS)))

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
                    self.custom_quotas = cfg.get('quotas', {})
                    self.is_docked_notch = cfg.get('docked_notch', False)
                    if self.is_docked_notch:
                        self.notch_morph_progress = 1.0
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
                    'provider_idx': self.selected_provider_idx,
                    'quotas': self.custom_quotas,
                    'docked_notch': self.is_docked_notch
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

    def get_current_monitor_rect(self):
        try:
            hmon = win32api.MonitorFromWindow(self.hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            info = win32api.GetMonitorInfo(hmon)
            return info['Monitor']
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

        # Render target components immediately on click (eliminates all latency/delay)
        self.hit_zones.clear()
        self.is_animating = True
        for item in self.canvas.find_all():
            if 'bg' not in self.canvas.gettags(item):
                self.canvas.delete(item)

        if self.current_view == 'min':
            self.render_min(int(tw), int(th))
        elif self.current_view == 'normal':
            self.render_normal(int(tw), int(th))
        else:
            self.render_detailed(int(tw), int(th))

        self.canvas.tag_lower('bg')

        # Keep capsule background at exact CURRENT dimensions so there is zero corner jumping
        self.update_morph_layout(int(self.curr_w), int(self.curr_h), int(self.curr_r))
        self.is_animating = True
        self.is_dirty = False
        self.save_config()

    def on_mouse_enter(self, event):
        self.is_hovered = True
        if self.current_view == 'min' and not self.is_animating:
            m_left, m_top, m_right, m_bottom = self.get_current_monitor_workarea()
            # Expand horizontally to 350px for ample breathing room during hover peek
            nw = 350.0
            nh = float(VIEW_SPECS['min'][1])
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
        self._last_drag_pos = (int(self.curr_x), int(self.curr_y))

    def on_drag(self, event):
        cur_pos = win32api.GetCursorPos()
        dx = cur_pos[0] - self._drag_start_x
        dy = cur_pos[1] - self._drag_start_y
        # Use 6px drag threshold to distinguish intentional drag from clicking
        if abs(dx) > 6 or abs(dy) > 6:
            self._dragging = True
            self._was_dragged = True
            nx = int(self._orig_win_x + dx)
            ny = int(self._orig_win_y + dy)
            if getattr(self, '_last_drag_pos', None) != (nx, ny):
                self._last_drag_pos = (nx, ny)
                self.curr_x = float(nx)
                self.curr_y = float(ny)
                self.target_x = self.curr_x
                self.target_y = self.curr_y
                self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)
                # SWP_MOVE_FLAGS passes SWP_NOSIZE so Windows never touches window sizing/DC buffers during drag
                user32.SetWindowPos(self.hwnd, 0, nx, ny, 0, 0, SWP_MOVE_FLAGS)

    def on_release(self, event):
        self._dragging = False
        if self._was_dragged:
            self._was_dragged = False
            rect = win32gui.GetWindowRect(self.hwnd)
            self.curr_x = float(rect[0])
            self.curr_y = float(rect[1])

            # Magnetic Screen-Top Notch Docking Check:
            # If user drops the widget within 16px of the physical monitor's top edge, snap into hardware notch mode!
            mon_rect = self.get_current_monitor_rect()
            top_edge = float(mon_rect[1])
            dist_to_top = abs(self.curr_y - top_edge)
            if dist_to_top <= 16.0:
                self.is_docked_notch = True
                self.target_y = top_edge
                self.curr_y = top_edge
                user32.SetWindowPos(self.hwnd, 0, int(self.curr_x), int(top_edge), 0, 0, SWP_MOVE_FLAGS)
            else:
                self.is_docked_notch = False
                self.target_y = self.curr_y

            self.target_x = self.curr_x
            self.anchor_center_x = self.curr_x + (self.curr_w / 2.0)
            self.is_dirty = True
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

    def get_account_quota_limit(self, prov_name, acc_id_or_email):
        # Check custom override first
        if acc_id_or_email in self.custom_quotas:
            return self.custom_quotas[acc_id_or_email]
        if prov_name in self.custom_quotas:
            return self.custom_quotas[prov_name]
        return self.default_account_quotas.get(prov_name, self.default_account_quotas['default'])

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

    def fetch_live_quota_for_connection(self, conn_id):
        # Non-blocking: returns immediately from cache, kicks off background worker if stale
        if not self.is_9router_running or not conn_id:
            return None
        now = time.time()
        cached = self.live_quotas_cache.get(conn_id)
        is_stale = (not cached) or (now - cached['time']) >= 15.0

        if is_stale and conn_id not in self._fetching_conn_ids:
            self._fetching_conn_ids.add(conn_id)
            threading.Thread(target=self._async_fetch_live_quota, args=(conn_id,), daemon=True).start()

        return cached['data'] if cached else None

    def _async_fetch_live_quota(self, conn_id):
        try:
            url = f'http://127.0.0.1:20128/api/usage/{conn_id}'
            req = urllib.request.Request(url, headers={'User-Agent': 'DynamicTokenHUD/1.0'})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read())
                    self.live_quotas_cache[conn_id] = {'time': time.time(), 'data': data}
                    self.is_dirty = True
        except Exception:
            pass
        finally:
            self._fetching_conn_ids.discard(conn_id)

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
                    self.last_activity_is_error = False
                    latest_call = cur.execute('SELECT promptTokens, completionTokens, status FROM usageHistory WHERE id = ?', (max_id,)).fetchone()
                    if latest_call:
                        self.last_delta_tokens = (latest_call[0] or 0) + (latest_call[1] or 0)
                        self.last_delta_time = time.time()
                        if latest_call[2] != 'ok':
                            self.last_activity_is_error = True
                self.last_max_id = max_id

            # Detect errors (e.g. 429 quota exhaustion, upstream failure) from requestDetails
            rd_latest = cur.execute('SELECT rowid, status, data FROM requestDetails ORDER BY rowid DESC LIMIT 1').fetchone()
            if rd_latest:
                rd_rowid, rd_status, rd_data_str = rd_latest
                if rd_rowid > self.last_rd_rowid:
                    if self.last_rd_rowid != 0:
                        if rd_status == 'error':
                            self.last_activity_time = time.time()
                            self.last_activity_is_error = True
                            self.is_dirty = True
                    self.last_rd_rowid = rd_rowid

                # Calculate real-time token speed (tokens per second)
                try:
                    rd_obj = json.loads(rd_data_str)
                    lat_obj = rd_obj.get('latency', {})
                    tok_obj = rd_obj.get('tokens', {})
                    c_tok = tok_obj.get('completion_tokens', 0)
                    tot_ms = lat_obj.get('total', 0)
                    ttft_ms = lat_obj.get('ttft', 0)
                    gen_ms = tot_ms - ttft_ms
                    if c_tok > 0 and gen_ms >= 80:
                        self.latest_tps = c_tok / (gen_ms / 1000.0)
                    elif c_tok > 0 and tot_ms >= 100:
                        self.latest_tps = c_tok / (tot_ms / 1000.0)
                except Exception:
                    pass

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

            # Current Quota is strictly based on today's current usage, independent of timeline selection
            curr_quota_acc_tokens = {}
            t_row = cur.execute('SELECT data FROM usageDaily WHERE dateKey = ?', (today_str,)).fetchone()
            if t_row:
                try:
                    td = json.loads(t_row[0])
                    for acc_id, a_stat in td.get('byAccount', {}).items():
                        curr_quota_acc_tokens[acc_id] = (a_stat.get('promptTokens', 0) or 0) + (a_stat.get('completionTokens', 0) or 0)
                except Exception:
                    pass

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
                            today_acc_stats[acc_id] = {'requests': 0, 'promptTokens': 0, 'completionTokens': 0, 'cost': 0.0}
                        today_acc_stats[acc_id]['requests'] += a_stat.get('requests', 0)
                        today_acc_stats[acc_id]['promptTokens'] += a_stat.get('promptTokens', 0)
                        today_acc_stats[acc_id]['completionTokens'] += a_stat.get('completionTokens', 0)
                        today_acc_stats[acc_id]['cost'] += a_stat.get('cost', 0.0)
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
                a_toks = astats.get('promptTokens', 0) + astats.get('completionTokens', 0)
                a_cost = astats.get('cost', 0.0)
                # Current day quota tokens (strictly today, independent of timeline)
                a_curr_quota_toks = curr_quota_acc_tokens.get(r[0], 0)
                is_curr = (latest_conn_id and r[0] == latest_conn_id)

                # Parse conn data for resetAt/lastPingedResetAt
                a_reset_at = None
                if r[6]:
                    try:
                        c_data = json.loads(r[6])
                        a_reset_at = c_data.get('lastPingedResetAt') or c_data.get('resetsAt') or c_data.get('expiresAt')
                    except Exception:
                        pass

                providers_map[raw_prov].append({
                    'id': r[0],
                    'provider': raw_prov,
                    'short_user': short_user,
                    'full_email': full_email,
                    'priority': r[4],
                    'is_active': is_active,
                    'is_current': is_curr,
                    'reqs': a_reqs,
                    'toks': a_toks,
                    'cost': a_cost,
                    'quota_toks': a_curr_quota_toks,
                    'reset_at': a_reset_at
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

    def check_startup_registration(self):
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            # Resolve dynamic-token.bat relative to this script directory so it works for any user or install path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            bat_path = os.path.join(script_dir, 'dynamic-token.bat')
            if not os.path.exists(bat_path):
                bat_path = os.path.expandvars(r"%USERPROFILE%\dynamic-token\dynamic-token.bat")

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
                try:
                    val, _ = winreg.QueryValueEx(key, 'DynamicTokenHUD')
                    if val != f'"{bat_path}"':
                        winreg.SetValueEx(key, 'DynamicTokenHUD', 0, winreg.REG_SZ, f'"{bat_path}"')
                except FileNotFoundError:
                    # Default on: register startup so Task Manager shows it enabled by default
                    winreg.SetValueEx(key, 'DynamicTokenHUD', 0, winreg.REG_SZ, f'"{bat_path}"')
        except Exception:
            pass

    def check_9router_health(self):
        try:
            req = urllib.request.Request('http://127.0.0.1:20128', headers={'User-Agent': 'DynamicTokenHUD/1.0'})
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                running = resp.status in (200, 301, 302, 401, 403)
        except Exception:
            running = False
        if running != self.is_9router_running:
            self.is_9router_running = running
            self.is_dirty = True
        return running

    def run_9router(self):
        # 1. Check if 9router is already running
        already_up = self.check_9router_health()
        if not already_up:
            # Spawn 9router background process (hidden/tray mode without stealing focus or killing anything)
            cmd = os.path.expandvars(r"%APPDATA%\npm\9router.cmd")
            if not os.path.exists(cmd):
                cmd = "9router"
            try:
                creationflags = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
                subprocess.Popen([cmd, "--no-browser"], creationflags=creationflags, shell=False)
            except Exception:
                try:
                    subprocess.Popen(f'start /b "" "{cmd}" --no-browser', shell=True)
                except Exception:
                    pass

        # 2. Open 9router Web UI in default browser
        threading.Thread(target=self._open_web_ui, daemon=True).start()

    def _open_web_ui(self):
        for _ in range(12):
            if self.check_9router_health():
                break
            time.sleep(0.5)
        webbrowser.open('http://127.0.0.1:20128')

    def poll_loop(self):
        count = 0
        while True:
            self.fetch_database_data()
            count += 1
            if count % 3 == 0:
                self.check_9router_health()
            time.sleep(1.0)

    # --- 165Hz Harmonic Spring Loop (stiffness=169, damping=26) ---
    def tick_loop(self):
        now = time.perf_counter()
        dt = min(0.02, max(0.003, now - self.last_tick_time))
        self.last_tick_time = now

        stiffness = 169.0
        damping = 26.0

        morph_updated = False
        # Harmonic 2nd-order damped spring for Split Island morphing
        # Uses exact Apple Island spring coefficients (stiffness=169, damping=26) for fluid 165Hz organic motion
        force_split = (self.target_split - self.split_morph_progress) * 169.0 - self.vel_split * 26.0
        self.vel_split += force_split * dt
        self.split_morph_progress += self.vel_split * dt

        if abs(self.target_split - self.split_morph_progress) < 0.005 and abs(self.vel_split) < 0.01:
            if self.split_morph_progress != self.target_split:
                self.split_morph_progress = self.target_split
                self.vel_split = 0.0
                morph_updated = True
        else:
            morph_updated = True

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
                self.render()

            self.canvas.config(width=int(self.curr_w), height=int(self.curr_h))
            self.update_morph_layout(int(self.curr_w), int(self.curr_h), int(self.curr_r))
            user32.SetWindowPos(self.hwnd, 0, int(self.curr_x), int(self.curr_y), int(self.curr_w), int(self.curr_h), SWP_FLAGS)

        # Suspend full card/view re-rendering and pulse redraws while actively dragging
        if not self._dragging:
            self.pulse_frame_idx = (self.pulse_frame_idx + 1) % 32
            self.rim_glow_phase = (self.rim_glow_phase + 0.12) % (2 * math.pi)
            self.update_antialiased_dot()

            time_since_call = time.time() - self.last_activity_time

            # Update Split Island active condition:
            # Active when a call completed within 3.5 seconds AND latest_tps > 0 in min view
            want_split = (self.current_view == 'min' and time_since_call < 3.5 and getattr(self, 'latest_tps', None) is not None)
            self.target_split = 1.0 if want_split else 0.0

            # Update Notch Docking condition:
            target_notch = 1.0 if self.is_docked_notch else 0.0
            if abs(self.notch_morph_progress - target_notch) > 0.005:
                self.notch_morph_progress += (target_notch - self.notch_morph_progress) * min(1.0, dt * 16.0)
                morph_updated = True
            elif self.notch_morph_progress != target_notch:
                self.notch_morph_progress = target_notch
                morph_updated = True

            if morph_updated or time_since_call < 2.5:
                self.update_morph_layout(int(self.curr_w), int(self.curr_h), int(self.curr_r))

            if self.last_delta_time != 0 and (time.time() - self.last_delta_time) > 1.8:
                self.last_delta_time = 0
                self.is_dirty = True

            if not self.is_animating and self.is_dirty:
                self.render()
                self.is_dirty = False

        self.root.after(6, self.tick_loop)

    def draw_capsule_image(self, w, h, radius):
        # Render rounded geometry above display resolution, then downsample once.
        # This keeps the 1px perimeter from becoming stair-stepped at small sizes.
        scale = RASTER_SCALE
        rw, rh = max(1, w * scale), max(1, h * scale)
        rr = radius * scale
        border_col = PIL_BORDER_HOVER if self.is_hovered else PIL_BORDER

        is_split = (self.current_view == 'min' and self.split_morph_progress > 0.01)
        is_notch = (self.notch_morph_progress > 0.01)

        cache_key = (w, h, radius, border_col, round(self.split_morph_progress, 2), round(self.notch_morph_progress, 2))
        time_since_call = time.time() - self.last_activity_time
        if time_since_call >= 2.5 and not getattr(self, 'is_animating', False) and cache_key in self._capsule_cache:
            return self._capsule_cache[cache_key]

        # Composite onto the color-key background before downsampling.
        im = Image.new('RGBA', (rw, rh), (*PIL_TRANSPARENT_RGB, 0))
        draw = ImageDraw.Draw(im)

        # Determine geometry for Notch Docking vs Floating Island
        # When notch_morph_progress > 0.0, top corners smoothly flatten
        top_corners = not is_notch

        if is_split:
            # Dual Capsule Ejection geometry:
            # Capsule 1 (Left main pill): [0, 0, main_w, h]
            # Capsule 2 (Right detached activity bubble): [main_w + gap, 0, w, h]
            gap_scaled = int(self.split_bubble_gap * self.split_morph_progress * scale)
            b_w_scaled = int(self.split_bubble_w * scale)
            main_rw = rw - gap_scaled - b_w_scaled
            r_bubble = rh // 2

            # Left capsule
            draw.rounded_rectangle([0, 0, main_rw - 1, rh - 1], radius=rr, fill=PIL_ISLAND_BG, corners=(top_corners, top_corners, True, True))
            draw.rounded_rectangle([0, 0, main_rw - 1, rh - 1], radius=rr, outline=border_col, width=scale, corners=(top_corners, top_corners, True, True))

            # Right detached bubble
            bx1 = main_rw + gap_scaled
            bx2 = rw - 1
            draw.rounded_rectangle([bx1, 0, bx2, rh - 1], radius=r_bubble, fill=PIL_ISLAND_BG)
            draw.rounded_rectangle([bx1, 0, bx2, rh - 1], radius=r_bubble, outline=border_col, width=scale)

            # Specular rim glow
            if time_since_call < 2.5:
                intensity = max(0.0, 1.0 - (time_since_call / 2.5))
                pulse_brightness = (math.sin(self.rim_glow_phase * 2.0) + 1.0) / 2.0
                alpha = int(220 * intensity * (0.6 + pulse_brightness * 0.4))
                glow_rgb = PIL_RIM_GLOW_ERROR_RGB if getattr(self, 'last_activity_is_error', False) else PIL_RIM_GLOW_RGB
                rim_col = (*glow_rgb, alpha)
                draw.rounded_rectangle([0, 0, main_rw - 1, rh - 1], radius=rr, outline=rim_col, width=3 * scale, corners=(top_corners, top_corners, True, True))
                draw.rounded_rectangle([bx1, 0, bx2, rh - 1], radius=r_bubble, outline=rim_col, width=3 * scale)
        else:
            # Single continuous capsule
            draw.rounded_rectangle([0, 0, rw - 1, rh - 1], radius=rr, fill=PIL_ISLAND_BG, corners=(top_corners, top_corners, True, True))
            draw.rounded_rectangle([0, 0, rw - 1, rh - 1], radius=rr, outline=border_col, width=scale, corners=(top_corners, top_corners, True, True))

            if time_since_call < 2.5:
                intensity = max(0.0, 1.0 - (time_since_call / 2.5))
                pulse_brightness = (math.sin(self.rim_glow_phase * 2.0) + 1.0) / 2.0
                alpha = int(220 * intensity * (0.6 + pulse_brightness * 0.4))
                glow_rgb = PIL_RIM_GLOW_ERROR_RGB if getattr(self, 'last_activity_is_error', False) else PIL_RIM_GLOW_RGB
                rim_col = (*glow_rgb, alpha)
                draw.rounded_rectangle([0, 0, rw - 1, rh - 1], radius=rr, outline=rim_col, width=3 * scale, corners=(top_corners, top_corners, True, True))

        # Flatten the resized edge onto the asymmetric color-key background.
        result = im.resize((w, h), Image.Resampling.LANCZOS)
        key_bg = Image.new('RGBA', result.size, (*PIL_TRANSPARENT_RGB, 255))
        result = Image.alpha_composite(key_bg, result).convert('RGB')
        if time_since_call >= 2.5 and not getattr(self, 'is_animating', False):
            self._capsule_cache[cache_key] = result
        return result

    def update_morph_layout(self, w, h, radius):
        rim_active = time.time() - self.last_activity_time < 2.5
        is_split = (self.current_view == 'min' and self.split_morph_progress > 0.01)
        is_notch = (self.notch_morph_progress > 0.01)
        now = time.perf_counter()

        # Discretize morph progress into subtle steps to allow caching without visual stepping
        split_step = round(self.split_morph_progress, 2)
        notch_step = round(self.notch_morph_progress, 2)
        paint_key = (w, h, radius, self.is_hovered, split_step, notch_step)

        if paint_key not in self._capsule_photo_cache:
            self._capsule_photo_cache[paint_key] = ImageTk.PhotoImage(self.draw_capsule_image(w, h, radius))
        self.bg_photo = self._capsule_photo_cache[paint_key]

        if not self.canvas.find_withtag('bg'):
            self.canvas.create_image(0, 0, anchor='nw', image=self.bg_photo, tags='bg')
        else:
            self.canvas.itemconfig('bg', image=self.bg_photo)

        # Hardware-level window shape clipping: ONLY update when geometry step actually changes!
        # Repeatedly calling SetWindowRgn every frame stalls the Windows DWM compositor.
        rgn_state = (w, h, radius, is_split, int(self.split_bubble_gap * self.split_morph_progress), is_notch)
        if getattr(self, '_last_rgn_state', None) != rgn_state:
            self._last_rgn_state = rgn_state
            try:
                if is_split:
                    gap = int(self.split_bubble_gap * self.split_morph_progress)
                    bw = int(self.split_bubble_w)
                    main_w = w - gap - bw
                    hrgn_main = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, int(main_w) + 1, int(h) + 1, int(radius * 2), int(radius * 2))
                    if is_notch:
                        hrgn_rect = ctypes.windll.gdi32.CreateRectRgn(0, 0, int(main_w) + 1, int(radius) + 1)
                        hrgn_notch = ctypes.windll.gdi32.CreateRectRgn(0, 0, 0, 0)
                        ctypes.windll.gdi32.CombineRgn(hrgn_notch, hrgn_rect, hrgn_main, 2)
                        ctypes.windll.gdi32.DeleteObject(hrgn_main)
                        ctypes.windll.gdi32.DeleteObject(hrgn_rect)
                        hrgn_main = hrgn_notch

                    hrgn_bubble = ctypes.windll.gdi32.CreateRoundRectRgn(int(main_w + gap), 0, int(w) + 1, int(h) + 1, int(h), int(h))
                    hrgn_comb = ctypes.windll.gdi32.CreateRectRgn(0, 0, 0, 0)
                    ctypes.windll.gdi32.CombineRgn(hrgn_comb, hrgn_main, hrgn_bubble, 2)
                    ctypes.windll.gdi32.DeleteObject(hrgn_main)
                    ctypes.windll.gdi32.DeleteObject(hrgn_bubble)
                    user32.SetWindowRgn(self.hwnd, hrgn_comb, False)
                elif is_notch:
                    hrgn_round = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, int(w) + 1, int(h) + 1, int(radius * 2), int(radius * 2))
                    hrgn_rect = ctypes.windll.gdi32.CreateRectRgn(0, 0, int(w) + 1, int(radius) + 1)
                    hrgn_notch = ctypes.windll.gdi32.CreateRectRgn(0, 0, 0, 0)
                    ctypes.windll.gdi32.CombineRgn(hrgn_notch, hrgn_rect, hrgn_round, 2)
                    ctypes.windll.gdi32.DeleteObject(hrgn_round)
                    ctypes.windll.gdi32.DeleteObject(hrgn_rect)
                    user32.SetWindowRgn(self.hwnd, hrgn_notch, False)
                else:
                    hrgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, int(w) + 1, int(h) + 1, int(radius * 2), int(radius * 2))
                    user32.SetWindowRgn(self.hwnd, hrgn, False)
            except Exception:
                pass

        cy = h // 2
        if self.current_view == 'min':
            if is_split:
                gap = int(self.split_bubble_gap * self.split_morph_progress)
                bw = int(self.split_bubble_w)
                main_w = w - gap - bw
                if self.canvas.find_withtag('min_right'):
                    self.canvas.coords('min_right', main_w - 18, cy)
                if self.canvas.find_withtag('min_left'):
                    self.canvas.coords('min_left', 36, cy)
                if self.canvas.find_withtag('dot_img'):
                    self.canvas.coords('dot_img', 20 - 14, cy - 14)
                if self.canvas.find_withtag('split_bubble_text'):
                    self.canvas.coords('split_bubble_text', main_w + gap + (bw // 2), cy)
            else:
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
        if is_active and getattr(self, 'last_activity_is_error', False):
            frame_list = self.dot_error_frames
        elif is_active:
            frame_list = self.dot_active_frames
        else:
            frame_list = self.dot_normal_frames
        img = frame_list[self.pulse_frame_idx]
        self.canvas.itemconfig('dot_img', image=img)

    def get_primary_reset_time_left(self):
        providers = self.stats.get('providers_data', [])
        if not providers:
            return None
        # Check active/current provider's current account
        curr_prov = providers[0]
        accs = curr_prov.get('accounts', [])
        if not accs:
            return None
        # Find current or first active account
        target_acc = next((a for a in accs if a.get('is_current')), accs[0])
        cid = target_acc.get('id')
        live_data = self.fetch_live_quota_for_connection(cid)
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
        return format_time_left(reset_at)

    # --- VIEW: MINIMUM ---
    def render_min(self, w, h):
        cy = h // 2
        self.place_dot(20, cy)

        raw_m = self.stats['latest_model']
        clean_m = clean_model_display_name(raw_m)
        short_m = clean_m.replace('gemini-', '').replace('flash-', 'f').replace('thinking', 'thk')

        is_split = (self.split_morph_progress > 0.01)
        gap = int(self.split_bubble_gap * self.split_morph_progress)
        bw = int(self.split_bubble_w)
        main_w = w - gap - bw if is_split else w

        is_flying_delta = (self.last_delta_time != 0) and ((time.time() - self.last_delta_time) < 1.8)
        if is_flying_delta:
            right_text = f"+{format_num(self.last_delta_tokens)} tok"
            text_color = HEX_GREEN
        elif self.is_hovered:
            # Hover peek: show live token speed and/or quota reset countdown
            peek_parts = []
            if getattr(self, 'latest_tps', None):
                peek_parts.append(f"{self.latest_tps:.0f} tok/s")
            reset_left = self.get_primary_reset_time_left()
            if reset_left:
                peek_parts.append(f"Resets {reset_left}")
            right_text = " • ".join(peek_parts) if peek_parts else f"{self.latest_tps:.0f} tok/s" if getattr(self, 'latest_tps', None) else "Peek Ready"
            text_color = HEX_ORANGE if getattr(self, 'latest_tps', None) else HEX_TEXT_PRIMARY
        else:
            tot_tok = self.stats['prompt'] + self.stats['completion']
            tok_str = format_num(tot_tok)
            cost_str = f"${self.stats['cost']:.2f}"
            right_text = f"{tok_str} tok • {cost_str}"
            text_color = HEX_TEXT_PRIMARY

        f9b = self.font_cache[('f', 9, 'bold')]
        right_w = f9b.measure(right_text)
        right_anchor_x = (main_w - 18) if is_split else (w - 24)

        # Responsive calculation of available width for left model text
        avail_left_w = max(40, (right_anchor_x - right_w - 14) - 36)
        disp_m = truncate_text_to_pixel_width(f9b, short_m, avail_left_w)

        self.canvas.create_text(
            36, cy, anchor='w',
            text=disp_m,
            fill=HEX_TEXT_SECONDARY,
            font=(FONT_NAME, 9, 'bold'),
            tags='min_left'
        )

        self.canvas.create_text(
            right_anchor_x, cy, anchor='e',
            text=right_text,
            fill=text_color,
            font=(FONT_NAME, 9, 'bold'),
            tags='min_right'
        )

        # If split is active, render detached activity bubble content (e.g. ⚡ 548)
        if is_split and self.split_morph_progress > 0.3:
            bubble_cx = main_w + gap + (bw // 2)
            tps_val = getattr(self, 'latest_tps', 0.0) or 0.0
            bubble_txt = f"{tps_val:.0f}" if tps_val > 0 else "⚡"
            self.canvas.create_text(
                bubble_cx, cy, anchor='center',
                text=bubble_txt,
                fill=HEX_ORANGE,
                font=(FONT_NAME, 9, 'bold'),
                tags='split_bubble_text'
            )

    # --- VIEW: NORMAL ---
    def render_normal(self, w, h):
        self.place_dot(22, 24)

        # Timeline tabs sit on the right at w - 22, taking ~160px
        tabs_w = 170
        avail_title_w = (w - 22 - tabs_w - 14) - 40
        f10b = self.font_cache[('f', 10, 'bold')]

        raw_m = self.stats['latest_model']
        clean_m = clean_model_display_name(raw_m)
        disp_m = truncate_text_to_pixel_width(f10b, clean_m, avail_title_w)

        self.canvas.create_text(
            40, 24, anchor='w',
            text=disp_m,
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
            spd_info = f" • {self.latest_tps:.0f} tok/s" if getattr(self, 'latest_tps', None) else ""
            m_cleaned = clean_model_display_name(last_call[3])
            ticker_txt = f"Last: {t_ago} • {m_cleaned} • +{format_num(last_call[4] + last_call[5])} tok{lat_info}{spd_info}"
        else:
            ticker_txt = "Listening for API calls..."

        f9 = self.font_cache[('f', 9, 'normal')]
        avail_ticker_w = (w - 22 - 38) - 22
        disp_ticker = truncate_text_to_pixel_width(f9, ticker_txt, avail_ticker_w)

        self.canvas.create_text(
            22, 104, anchor='w',
            text=disp_ticker,
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

        # 1. Header (y=24)
        self.place_dot(24, 24)

        self.canvas.create_text(
            44, 24, anchor='w',
            text='Token Usage & API Call History',
            fill=HEX_TEXT_PRIMARY,
            font=(FONT_NAME, 11, 'bold')
        )

        # Header Controls: 9router runner, Minimize and Shutdown
        r_txt = "9R"
        r_fill = '#381C08' if self.is_9router_running else '#281506'
        r_border = '#8A420A' if self.is_9router_running else '#542605'
        r_fg = '#FF9F0A'
        self.draw_circle_button(w - 92, 24, r=12, text=r_txt, callback=self.run_9router, bg=r_fill, fg=r_fg, border=r_border)
        self.draw_circle_button(w - 62, 24, r=12, text='minimize', callback=lambda: self.set_view('min'))
        self.draw_circle_button(w - 32, 24, r=12, text='close', callback=self.shutdown, bg='#241416', fg='#FF453A', border='#4A1E22')

        # Row 2 (y=54): Timeline Tabs & Latency Metric
        self.render_timeline_tabs(24, 54, anchor='w')

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
                speed_str = f" • {self.latest_tps:.0f} tok/s" if getattr(self, 'latest_tps', None) else ""
                lat_txt = f"{tot_ms / 1000.0:.2f}s (TTFT {ttft_ms}ms){speed_str}"

        self.canvas.create_text(
            w - 24, 54, anchor='e',
            text=lat_txt,
            fill=lat_color,
            font=(FONT_NAME, 8, 'bold')
        )

        # 2. PRIMARY METRICS CARD (y=74, h=66)
        tot_tok = self.stats['prompt'] + self.stats['completion']
        prompt_tok = self.stats['prompt']
        cached_tok = self.stats['cached']
        cost = self.stats['cost']
        reqs = self.stats['requests']
        reasoning_tok = self.stats['reasoning']
        cache_pct = (cached_tok / prompt_tok * 100) if prompt_tok > 0 else 0.0

        box_y1 = 74
        box_h = 66

        self.draw_rounded_card('stat_card', box_x1, box_y1, box_w, box_h, radius=16)

        col_w = box_w // 5
        self.canvas.create_text(box_x1 + 14, box_y1 + 18, anchor='w', text='TOTAL TOKENS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + 14, box_y1 + 44, anchor='w', text=format_num(tot_tok), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w + 14, box_y1 + 18, anchor='w', text='BURN COST', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w + 14, box_y1 + 44, anchor='w', text=f"${cost:.2f}", fill=HEX_GREEN, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 2 + 14, box_y1 + 18, anchor='w', text='REQUESTS', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 2 + 14, box_y1 + 44, anchor='w', text=format_num(reqs), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 3 + 14, box_y1 + 18, anchor='w', text='CACHE RATIO', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 3 + 14, box_y1 + 44, anchor='w', text=f"{cache_pct:.1f}%", fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        self.canvas.create_text(box_x1 + col_w * 4 + 14, box_y1 + 18, anchor='w', text='THINKING', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 8, 'bold'))
        self.canvas.create_text(box_x1 + col_w * 4 + 14, box_y1 + 44, anchor='w', text=format_num(reasoning_tok), fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 13, 'bold'))

        # 3. DEDICATED SECTION: ACCOUNT MANAGER (y=154, h=124)
        pool_header_y = 154
        self.canvas.create_text(24, pool_header_y, anchor='w', text='ACCOUNT MANAGER', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        # Dedicated Refresh Pill Button with visible text and click feedback (x1=182 gives clean 20px gap from title)
        is_recently_refreshed = (time.time() - getattr(self, '_last_refresh_click', 0)) < 1.2
        ref_text = "✓ Updated" if is_recently_refreshed else "⟳ Refresh"
        ref_fg = HEX_GREEN if is_recently_refreshed else HEX_TEXT_SECONDARY
        ref_bg = '#142A1A' if is_recently_refreshed else '#1C1C1F'
        ref_border = '#1E5E2A' if is_recently_refreshed else '#333338'
        self.draw_pill_button_styled(182, pool_header_y - 10, 256, pool_header_y + 10, ref_text,
                                    callback=self.trigger_refresh, fill=ref_bg, fg=ref_fg, border=ref_border, radius=8)

        providers = self.stats.get('providers_data', [])
        num_providers = len(providers)
        if num_providers > 0:
            p_idx = self.selected_provider_idx % num_providers
            curr_prov = providers[p_idx]
        else:
            p_idx = 0
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

        # Account Manager Card Container (Height tuned to 120px)
        pool_box_y = pool_header_y + 14
        pool_box_h = 120

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

        # Right Column: Interactive Account Slot Selector (Clickable 1..N) with rounded pills
        chain_w = 210
        chain_x_start = box_x1 + box_w - chain_w
        self.canvas.create_text(chain_x_start, pool_box_y + 16, anchor='w', text='SELECT ACCOUNT', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 7, 'bold'))

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

            bx1, by1 = slot_x, pool_box_y + 30
            bx2, by2 = slot_x + 22, pool_box_y + 52

            self.draw_pill_button_styled(bx1, by1, bx2, by2, str(p_num),
                                        callback=lambda idx=i, pr=prov_raw: self.select_account_slot(pr, idx),
                                        fill=btn_fill, fg=btn_fg, border=btn_border, radius=6)
            slot_x += 26

        if displayed_acc:
            acc_name = displayed_acc.get('full_email') or displayed_acc.get('name') or '--'
            is_curr = displayed_acc.get('is_current', False)
            is_on = displayed_acc.get('is_active', False)

            status_text = "Active Route" if is_curr else ("Standby Ready" if is_on else "Disabled")
            status_color = HEX_GREEN if is_curr else (HEX_TEXT_PRIMARY if is_on else HEX_TEXT_MUTED)

            # CURRENT QUOTA: Check live 9router quota first (tracks resets accurately), fallback to daily ledger
            disp_cid = displayed_acc.get('id')
            live_data = self.fetch_live_quota_for_connection(disp_cid)
            live_quota_used_pct = None
            live_reset_at = None
            if live_data and 'quotas' in live_data:
                # Find matching model quota from 9router (e.g. gemini-3.8-flash-high or main quota)
                q_dict = live_data['quotas']
                best_q = None
                latest_m = self.stats.get('latest_model', '')
                for m_candidate in [latest_m, 'gemini-3.8-flash-high', 'claude-opus-4-6-thinking', 'gpt-5.6-luna']:
                    if m_candidate in q_dict:
                        best_q = q_dict[m_candidate]
                        break
                if not best_q and q_dict:
                    best_q = next(iter(q_dict.values()))
                if best_q and 'remainingPercentage' in best_q:
                    live_quota_used_pct = max(0.0, min(100.0, 100.0 - float(best_q['remainingPercentage'])))
                    live_reset_at = best_q.get('resetAt')

            # Fallback 1: check connection metadata for resetAt/expiresAt
            if not live_reset_at and displayed_acc.get('reset_at'):
                live_reset_at = displayed_acc['reset_at']

            # Fallback 2: next UTC midnight (standard daily quota reset boundary)
            if not live_reset_at:
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                live_reset_at = (now_utc + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

            reset_time_left_str = format_time_left(live_reset_at)

            acc_limit = self.get_account_quota_limit(prov_raw, acc_name)
            if live_quota_used_pct is not None:
                acc_pct = live_quota_used_pct
                acc_ratio = acc_pct / 100.0
                acc_quota_used = int(acc_limit * acc_ratio)
            else:
                acc_quota_used = displayed_acc.get('quota_toks', 0)
                acc_ratio = min(1.0, acc_quota_used / (acc_limit if acc_limit > 0 else 1))
                acc_pct = (acc_quota_used / acc_limit * 100.0) if acc_limit > 0 else 0.0

            # TIMELINE SYNCHRONIZED TOKENS: Synchronized with timeline selection (today, 7D, 30D, All)
            timeline_toks = displayed_acc.get('toks', 0)
            timeline_reqs = displayed_acc.get('reqs', 0)
            t_label = 'Today' if self.timeline == 'today' else ('7D' if self.timeline == '7d' else ('30D' if self.timeline == '30d' else 'All-Time'))

            # Available horizontal width for the left side before hitting the account pills:
            max_left_w = chain_x_start - (box_x1 + 16) - 14  # ~346px

            # Line 1 (y=pool_box_y + 16): Responsive Account Name & Status Badge
            # Email is on left. Status badge is drawn as a dedicated Apple capsule pill tag at the right of the column
            status_tag_text = f"P{displayed_acc.get('priority', 1)}  •  {status_text}"
            tag_w = len(status_tag_text) * 6 + 18
            tag_x2 = box_x1 + 16 + max_left_w
            tag_x1 = tag_x2 - tag_w
            tag_fill = '#0B2915' if is_curr else ('#1A1A1D' if is_on else '#241416')
            tag_border = '#144D26' if is_curr else ('#333336' if is_on else '#4A1E22')
            tag_fg = HEX_GREEN if is_curr else (HEX_TEXT_PRIMARY if is_on else HEX_TEXT_MUTED)

            f10b = self.font_cache[('f', 10, 'bold')]
            avail_email_w = (tag_x1 - 12) - (box_x1 + 16)
            disp_email = truncate_text_to_pixel_width(f10b, acc_name, avail_email_w)

            # 1. Email text (Anchor 'w' on left)
            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 16, anchor='w',
                text=disp_email,
                fill=HEX_TEXT_PRIMARY,
                font=(FONT_NAME, 10, 'bold')
            )

            # 2. Apple status pill badge anchored on the right of the left sub-section
            self.draw_pill_button_styled(tag_x1, pool_box_y + 6, tag_x2, pool_box_y + 24, status_tag_text,
                                        callback=lambda: None, fill=tag_fill, fg=tag_fg, border=tag_border, radius=6)

            # Line 2 (y=pool_box_y + 38): Current Quota Status (Label + Reset countdown on left, Figures on right)
            quota_acc_str = f"{format_num(acc_quota_used)} / {format_num(acc_limit)} ({acc_pct:.1f}%)"
            quota_val_color = '#FF453A' if acc_pct >= 90 else ('#FF9F0A' if acc_pct >= 75 else HEX_TEXT_PRIMARY)
            f8b = self.font_cache[('f', 8, 'bold')]
            f7b = self.font_cache[('f', 7, 'bold')]
            quota_str_w = f8b.measure(quota_acc_str)

            avail_lbl_w = max(40, max_left_w - quota_str_w - 14)
            quota_label_txt = f"QUOTA  •  {reset_time_left_str}" if reset_time_left_str else "CURRENT QUOTA"
            disp_quota_lbl = truncate_text_to_pixel_width(f7b, quota_label_txt, avail_lbl_w)

            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 38, anchor='w',
                text=disp_quota_lbl,
                fill=HEX_TEXT_MUTED,
                font=(FONT_NAME, 7, 'bold')
            )
            self.canvas.create_text(
                box_x1 + 16 + max_left_w, pool_box_y + 38, anchor='e',
                text=quota_acc_str,
                fill=quota_val_color,
                font=(FONT_NAME, 8, 'bold')
            )

            # Line 3 (y=pool_box_y + 51): DEDICATED PROGRESS BAR (Capsule styled with rounded ends)
            bar_x1 = box_x1 + 16
            bar_x2 = bar_x1 + max_left_w
            bar_y1 = pool_box_y + 49
            bar_y2 = pool_box_y + 55
            self.draw_pill_button_styled(bar_x1, bar_y1, bar_x2, bar_y2, '', callback=lambda: None, fill='#202024', border='#28282C', radius=3)
            acc_bar_color = '#FF453A' if acc_pct >= 90 else ('#FF9F0A' if acc_pct >= 75 else HEX_GREEN)
            fill_w = int(max_left_w * acc_ratio)
            if fill_w > 4:
                self.draw_pill_button_styled(bar_x1, bar_y1, bar_x1 + fill_w, bar_y2, '', callback=lambda: None, fill=acc_bar_color, border=acc_bar_color, radius=3)

            # Line 4 (y=pool_box_y + 70): Individual Account Token Used (Synchronized with timeline)
            used_str = f"{t_label} Burn: {format_num(timeline_toks)} tokens • {timeline_reqs} requests"
            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 70, anchor='w',
                text=used_str,
                fill=HEX_TEXT_SECONDARY,
                font=(FONT_NAME, 8)
            )

            # Line 5 (y=pool_box_y + 94): Action Button & Provider Total summary
            acc_action_txt = "Deactivate Account" if is_on else "Activate Account"
            acc_btn_color = '#381618' if is_on else '#122E1A'
            acc_btn_border = '#662228' if is_on else '#1E5E2A'
            acc_text_color = '#FF6961' if is_on else HEX_GREEN

            ab_w = 124
            ab_h = 20
            ab_x1 = box_x1 + 16
            ab_y1 = pool_box_y + 90
            ab_x2 = ab_x1 + ab_w
            ab_y2 = ab_y1 + ab_h

            self.draw_pill_button_styled(ab_x1, ab_y1, ab_x2, ab_y2, acc_action_txt,
                                        callback=lambda cid=displayed_acc.get('id'), st=is_on: self.toggle_account_active(cid, st),
                                        fill=acc_btn_color, fg=acc_text_color, border=acc_btn_border, radius=9)

            # Details footnote on the right of the button
            self.canvas.create_text(
                ab_x2 + 14, (ab_y1 + ab_y2) // 2, anchor='w',
                text=f"Provider: {curr_prov['active_count']}/{curr_prov['total_count']} Active • {format_num(curr_prov['total_toks'])} tok",
                fill=HEX_TEXT_MUTED,
                font=(FONT_NAME, 8)
            )
        else:
            self.canvas.create_text(
                box_x1 + 16, pool_box_y + 47, anchor='w',
                text="No accounts registered for this provider",
                fill=HEX_TEXT_MUTED,
                font=(FONT_NAME, 9)
            )

        # 4. TOP MODELS BREAKDOWN (Apple iOS Storage/Battery style progress track)
        models_header_y = pool_box_y + pool_box_h + 16
        self.canvas.create_text(24, models_header_y, anchor='w', text='TOP MODELS BREAKDOWN', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        sorted_models = sorted(self.stats['models'].items(), key=lambda item: item[1]['prompt'], reverse=True)[:3]

        bar_y = models_header_y + 24
        f9 = self.font_cache[('f', 9, 'normal')]
        f8 = self.font_cache[('f', 8, 'normal')]
        for m_name, mdata in sorted_models:
            p_val = mdata['prompt'] + mdata['completion']
            r_val = mdata['requests']
            ratio = min(1.0, p_val / (tot_tok if tot_tok > 0 else 1))

            right_stat_str = f"{format_num(p_val)} tok ({r_val} reqs)"
            right_stat_w = f8.measure(right_stat_str)

            # Available width for model name: from x=24 up to (w - 24 - right_stat_w - 16)
            avail_model_w = (w - 24 - right_stat_w - 16) - 24
            clean_m = clean_model_display_name(m_name)
            disp_m = truncate_text_to_pixel_width(f9, clean_m, avail_model_w)

            self.canvas.create_text(24, bar_y, anchor='w', text=disp_m, fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9))
            self.canvas.create_text(w - 24, bar_y, anchor='e', text=right_stat_str, fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 8))

            bar_w_max = w - 48
            track_y1 = bar_y + 14
            track_y2 = bar_y + 20
            self.draw_pill_button_styled(24, track_y1, 24 + bar_w_max, track_y2, '', callback=lambda: None, fill='#202024', border='#28282C', radius=3)
            fill_bar_w = int(bar_w_max * ratio)
            if fill_bar_w > 4:
                self.draw_pill_button_styled(24, track_y1, 24 + fill_bar_w, track_y2, '', callback=lambda: None, fill='#E5E5EA', border='#E5E5EA', radius=3)
            bar_y += 32

        # 5. LIVE API CALL HISTORY (Rounded status badge pills)
        feed_header_y = bar_y + 6
        self.canvas.create_text(24, feed_header_y, anchor='w', text='LIVE API CALL HISTORY', fill=HEX_TEXT_MUTED, font=(FONT_NAME, 9, 'bold'))

        feed_y = feed_header_y + 20
        for row in self.stats['recent'][:3]:
            t_ago = format_time_ago(row[1])
            m_tag = row[3]
            toks = row[4] + row[5]
            st = row[7]

            badge_fill = '#0B2915' if st == 'ok' else '#2D0E11'
            badge_border = '#144D26' if st == 'ok' else '#59181D'
            badge_fg = HEX_GREEN if st == 'ok' else '#FF453A'
            self.draw_pill_button_styled(24, feed_y - 2, 24 + 52, feed_y + 16, '200 OK' if st == 'ok' else 'ERR', callback=lambda: None, fill=badge_fill, fg=badge_fg, border=badge_border, radius=6)

            right_feed_str = f"+{format_num(toks)} tok • {t_ago}"
            right_feed_w = f9.measure(right_feed_str)

            # Available width for model label between badge (x=86) and right stats
            avail_feed_m_w = (w - 24 - right_feed_w - 16) - 86
            clean_feed_m = clean_model_display_name(m_tag)
            disp_feed_m = truncate_text_to_pixel_width(f9, clean_feed_m, avail_feed_m_w)

            self.canvas.create_text(86, feed_y + 7, anchor='w', text=disp_feed_m, fill=HEX_TEXT_PRIMARY, font=(FONT_NAME, 9))
            self.canvas.create_text(w - 24, feed_y + 7, anchor='e', text=right_feed_str, fill=HEX_TEXT_SECONDARY, font=(FONT_NAME, 9))
            feed_y += 22

    # --- UI Helpers & Rounded Card Rasterizers ---
    def rounded_image(self, width, height, radius, fill, border, outline_width=1):
        # Supersample all rounded geometry so borders share one smooth rendering path.
        scale = RASTER_SCALE
        image = Image.new('RGBA', (width * scale, height * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            [0, 0, width * scale - 1, height * scale - 1],
            radius=radius * scale,
            fill=fill,
            outline=border,
            width=max(1, outline_width * scale)
        )
        # Return RGBA image directly with true alpha so sub-elements overlay cleanly
        # on the dark capsule without colorkey punch-through forming rectangular corners.
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def draw_rounded_card(self, cache_key, x, y, width, height, radius=16):
        card_key = f"{cache_key}_{width}_{height}_{radius}"
        if card_key not in self.card_photos:
            self.card_photos[card_key] = ImageTk.PhotoImage(
                self.rounded_image(width, height, radius, PIL_CARD_BG, PIL_CARD_BORDER)
            )
        self.canvas.create_image(x, y, anchor='nw', image=self.card_photos[card_key])

    def draw_pill_button_styled(self, x1, y1, x2, y2, text, callback, fill='#1C1C1F', fg=HEX_TEXT_PRIMARY, border=HEX_BORDER, radius=8):
        bw = max(4, x2 - x1)
        bh = max(4, y2 - y1)
        key = f"pill_{bw}_{bh}_{fill}_{border}_{radius}"
        if key not in self.card_photos:
            self.card_photos[key] = ImageTk.PhotoImage(
                self.rounded_image(bw, bh, radius, fill, border)
            )

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
                bg_c = PIL_TAB_ACTIVE if is_active else PIL_TAB_INACTIVE
                bd_c = (60, 60, 64, 255) if is_active else (32, 32, 35, 255)
                self.card_photos[tab_img_key] = ImageTk.PhotoImage(
                    self.rounded_image(tab_w, tab_h, 12, bg_c, bd_c)
                )

            self.canvas.create_image(bx1, by1, anchor='nw', image=self.card_photos[tab_img_key])
            fg = HEX_TEXT_PRIMARY if is_active else HEX_TEXT_MUTED
            self.canvas.create_text((bx1 + bx2) // 2, (by1 + by2) // 2, text=label, fill=fg, font=(FONT_NAME, 8, 'bold'))

            def make_handler(k):
                return lambda: self.switch_timeline(k)

            self.hit_zones.append((bx1, by1, bx2, by2, make_handler(key)))

    def draw_circle_button(self, cx, cy, r, text, callback, bg='#1C1C1E', fg=HEX_TEXT_PRIMARY, border=HEX_BORDER):
        size = (r * 2) + 1
        key = f"circle_{size}_{bg}_{border}"
        if key not in self.card_photos:
            self.card_photos[key] = ImageTk.PhotoImage(
                self.rounded_image(size, size, r, bg, border)
            )
        self.canvas.create_image(cx - r, cy - r, anchor='nw', image=self.card_photos[key])

        if text in ('close', '✕'):
            # Geometric cross, not a font glyph: stable weight and optical centering.
            d = 4
            self.canvas.create_line(cx - d, cy - d, cx + d, cy + d, fill=fg, width=2, capstyle='round')
            self.canvas.create_line(cx - d, cy + d, cx + d, cy - d, fill=fg, width=2, capstyle='round')
        elif text == 'minimize':
            self.canvas.create_line(cx - 4, cy, cx + 4, cy, fill=fg, width=2, capstyle='round')
        elif text == 'refresh':
            # Apple-style geometric circular arc with arrowhead for refresh
            self.canvas.create_arc(cx - 4, cy - 4, cx + 4, cy + 4, start=45, extent=270, style='arc', outline=fg, width=1.6)
            self.canvas.create_line(cx + 1, cy - 5, cx + 4, cy - 3, fill=fg, width=1.6, capstyle='round')
            self.canvas.create_line(cx + 4, cy - 3, cx + 4, cy, fill=fg, width=1.6, capstyle='round')
        else:
            self.canvas.create_text(cx, cy, text=text, fill=fg, font=(FONT_NAME, 8, 'bold'))
        self.hit_zones.append((cx - r, cy - r, cx + r, cy + r, callback))

    def trigger_refresh(self):
        self._last_refresh_click = time.time()
        # Invalidate live quota cache so it immediately queries 9router in the background
        self.live_quotas_cache.clear()
        self._fetching_conn_ids.clear()
        self.fetch_database_data()
        self.check_9router_health()
        self.is_dirty = True
        self.render()

    def refresh_data(self):
        self.trigger_refresh()

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
