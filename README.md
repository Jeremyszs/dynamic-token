# Dynamic Token HUD (Apple Dynamic Island)

A lightweight, frameless floating HUD for Windows that monitors real-time LLM token burn, API call history, and costs from 9router.

Built with native Python and Win32 APIs for near-zero resource impact (~15MB RAM).

## Features
- **Apple Dynamic Island Aesthetics:** Pitch-black container, smooth pill/capsule corners, and a 4× supersampled anti-aliased live status indicator.
- **Harmonic Spring Motion:** Calibrated 2nd-order damped spring physics (`stiffness = 169.0`, `damping = 26.0`) with in-place glyph translation (zero canvas churn).
- **Three Interactive View Tiers:**
  - **Minimum:** Compact pill displaying active model, live token count, and cost.
  - **Normal:** Expanded card with timeline filters, large typography, requests count, and last executed request ticker.
  - **Detailed:** 4-card metric breakdown (Total Tokens, Cost, Requests, Cache Hit Ratio), ranked model progress bars, live API log with HTTP status pills, and shutdown controls.
- **Multi-Monitor Safe:** Resolves true physical monitor bounds using `win32api.MonitorFromWindow`, preventing coordinate bounce when dragged between screens.
- **Embedded SF Pro Display:** Automatically registers Apple's system typeface into the Windows GDI font engine.

## Controls
- **Left-Click:** Cycle views (`Min` ➔ `Normal` ➔ `Detailed` ➔ `Min`).
- **Right-Click:** Instantly toggle between `Min` and `Detailed`.
- **Drag:** Click and hold anywhere to freely position across any monitor.
- **Close:** In Detailed mode, click `—` to collapse or `✕` to shut down the HUD process.

## Quick Start
```bash
# Launch directly
launch_island_hud.bat
```
