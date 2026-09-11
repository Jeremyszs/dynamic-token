# Dynamic Token HUD (Apple Dynamic Island)

A lightweight, frameless floating HUD for Windows that monitors real-time LLM token burn, API call history, and costs from 9router.

## Features
- **Apple Dynamic Island Aesthetics:** Pitch black container, smooth rounded pill geometry, pulsing live connection dot.
- **Three View Tiers:** Minimum pill, Normal card, and Detailed breakdown with timeline filters (`Today`, `7D`, `30D`, `All`).
- **Always-On-Top & Multi-Monitor Safe:** Floats over active windows, stays pinned across desktop tabs, and handles secondary displays without coordinate jumping.
- **Ultra-Lightweight:** Native Python/Win32 backend (~15MB RAM footprint).
- **SF Pro Display:** Embedded Apple typography.

## Quick Start
```bash
# Run launcher directly
launch_island_hud.bat
```
