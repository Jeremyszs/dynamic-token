# Dynamic Token HUD (Apple Dynamic Island)

A lightweight, frameless floating HUD for Windows that monitors real-time LLM token burn, API call history, and costs from [9router](https://github.com/Jeremyszs/9router).

Built with native Python and Win32 APIs for near-zero resource impact (~15MB RAM).

## Features
- **Apple Dynamic Island Aesthetics:** Pitch-black container, smooth pill/capsule corners, and a 4× supersampled anti-aliased live status indicator.
- **Harmonic Spring Motion:** Calibrated 2nd-order damped spring physics (`stiffness = 169.0`, `damping = 26.0`) with in-place glyph translation (zero canvas churn).
- **Dynamic Shape Transformations:**
  - **The Split Island (Dual Capsule Ejection):** When an API call completes with live token generation, an independent activity bubble smoothly detaches to the right of the main capsule displaying real-time speed (`⚡ 548 tok/s`), then snaps back into the unified capsule when idle.
  - **Magnetic Top-Notch Docking:** Dragging and releasing the widget near the physical top edge of any display causes the upper corners to seamlessly flatten (`r_top=0`, `r_bottom=21`), transforming the island into a hardware-style display notch flush with the screen bezel.
- **Three Interactive View Tiers:**
  - **Minimum:** Compact pill displaying active model, live token count, and cost. Features an **interactive hover peek** that smoothly expands on mouseover to reveal live generation throughput (`tok/s`) and quota reset countdown (`Resets 44m`).
  - **Normal:** Expanded card with timeline filters, large typography, requests count, and last executed request ticker.
  - **Detailed:** 5-metric overview (Total Tokens, Cost, Requests, Cache Hit Ratio, Thinking tokens), Carousel Account Manager with active provider controls, ranked model progress bars, live API log with HTTP status pills, 9router runner, and shutdown controls.
- **Integrated 9router Runner:** Header `9R` button checks daemon health, starts 9router in the background without stealing focus if stopped, and opens the Web UI.
- **Account Manager Refresh Button:** Dedicated circular refresh button beside `ACCOUNT MANAGER` to instantly sync quotas, accounts, and provider status from the database.
- **Error & Quota Exhaustion Alerts:** Automatically flashes red perimeter rim glow and switches the live top-left LED dot to red when 429 quota exhaustion or upstream errors occur.
- **Live Token Speedometer (`tok/s`):** Computes real-time generation throughput from completion tokens and generation duration, visible in both Normal ticker and Detailed latency rows.
- **Multi-Monitor Safe:** Resolves true physical monitor bounds using `win32api.MonitorFromWindow`, preventing coordinate bounce when dragged across screens.
- **Smooth 165Hz Dragging:** Position-only updates (`SWP_NOSIZE`) with deferred canvas rendering for zero-stutter dragging.
- **Embedded SF Pro Display:** Automatically registers Apple's system typeface into the Windows GDI font engine.
- **Auto-Start on Startup:** Automatically registers under Windows Startup (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`), manageable directly in Windows Task Manager.

---

## Installation Guide

### Prerequisites
- **Windows 10 / 11**
- **Python 3.10+** (with `pip` and added to `PATH`)
- **9router** (local proxy daemon logging to `%APPDATA%\9router\db\data.sqlite`)

### 1. Clone the Repository
```bash
git clone https://github.com/Jeremyszs/dynamic-token.git
cd dynamic-token
```

### 2. Install Dependencies
You can install dependencies into your system Python or a virtual environment:

```bash
# Recommended: virtual environment
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

*(Includes `PySide6` for GPU-accelerated Qt Quick / QML rendering, `Pillow`, and `pywin32`)*

### 3. Run the HUD
To run the modern GPU-accelerated PySide6 + Qt Quick version:
```bash
python -m app.main
```
Or use the launcher `dynamic-token.bat`. To run the legacy Tkinter fallback version:
```bash
python dynamic_island_hud.py
```

The launcher automatically detects:
1. `.\venv\Scripts\pythonw.exe` (local virtual environment)
2. `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\pythonw.exe` (Hermes environment)
3. System `pythonw` or `python` from `PATH`

---

## Controls
- **Hover Peek (`Min` mode):** Hover cursor over the compact pill to peek live token generation speed and quota reset countdown without clicking.
- **Left-Click:** Cycle views (`Min` ➔ `Normal` ➔ `Detailed` ➔ `Min`).
- **Right-Click:** Instantly toggle between `Min` and `Detailed`.
- **Drag:** Click and hold anywhere to freely position across any monitor.
- **Refresh Button (Account Manager):** Instantly re-reads 9router SQLite database and synchronizes all accounts, quotas, and provider states.
- **9R Button (Detailed view):** Opens 9router Web UI and starts background daemon if not already running.
- **Minimize (`—`):** Collapse back to `Min` capsule.
- **Close (`✕`):** Clean shutdown of the HUD process.

---

## Windows Startup & Auto-Launch

When launched, the widget automatically registers its full path to:
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run -> DynamicTokenHUD
```

* Works per-user without requiring Administrator privileges.
* To disable auto-start, open **Windows Task Manager (Ctrl + Shift + Esc) ➔ Startup apps ➔ right-click DynamicTokenHUD ➔ Disable**.
