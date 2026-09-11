# Dynamic Token HUD (Apple Dynamic Island)

A lightweight, frameless floating HUD for Windows that monitors real-time LLM token burn, API call history, and costs from [9router](https://github.com/Jeremyszs/9router).

Built with native Python and Win32 APIs for near-zero resource impact (~15MB RAM).

## Features
- **Apple Dynamic Island Aesthetics:** Pitch-black container, smooth pill/capsule corners, and a 4× supersampled anti-aliased live status indicator.
- **Harmonic Spring Motion:** Calibrated 2nd-order damped spring physics (`stiffness = 169.0`, `damping = 26.0`) with in-place glyph translation (zero canvas churn).
- **Three Interactive View Tiers:**
  - **Minimum:** Compact pill displaying active model, live token count, and cost.
  - **Normal:** Expanded card with timeline filters, large typography, requests count, and last executed request ticker.
  - **Detailed:** 5-metric overview (Total Tokens, Cost, Requests, Cache Hit Ratio, Thinking tokens), Carousel Account Manager with active provider controls, ranked model progress bars, live API log with HTTP status pills, 9router runner, and shutdown controls.
- **Integrated 9router Runner:** Header `9R` button checks daemon health, starts 9router in the background without stealing focus if stopped, and opens the Web UI.
- **Error & Quota Exhaustion Alerts:** Automatically flashes red perimeter rim glow and switches the live top-left LED dot to red when 429 quota exhaustion or upstream errors occur.
- **Live Token Speedometer (`tok/s`):** Computes real-time generation throughput from completion tokens and generation duration, visible in both Normal ticker and Detailed latency rows.
- **Global Summon Hotkey (`Win + Alt + D`):** Quick-toggle HUD visibility from any active application.
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

*(If you don't have a `requirements.txt`, install directly:)*
```bash
pip install pillow pywin32
```

### 3. Run the HUD
Double-click `dynamic-token.bat` or run from terminal:
```cmd
dynamic-token.bat
```

The launcher automatically detects:
1. `.\venv\Scripts\pythonw.exe` (local virtual environment)
2. `%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\pythonw.exe` (Hermes environment)
3. System `pythonw` or `python` from `PATH`

---

## Controls
- **Global Hotkey (`Win + Alt + D`):** Instantly toggle between `Min` capsule and `Detailed` sheet from anywhere in Windows (uses low-level Win32 hook to bypass Game Bar).
- **Left-Click:** Cycle views (`Min` ➔ `Normal` ➔ `Detailed` ➔ `Min`).
- **Right-Click:** Instantly toggle between `Min` and `Detailed`.
- **Drag:** Click and hold anywhere to freely position across any monitor.
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
