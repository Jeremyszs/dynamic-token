# Migration Plan: Native Tkinter -> PySide6 + Qt Quick/QML

## 1. Current Tkinter Architecture
- **Rendering & Animation**: Tkinter `Canvas` with an in-process 165Hz `tick_loop` (Euler integration spring physics `stiffness=169, damping=26`) calling PIL downsampling (`ImageDraw.rounded_rectangle`, Lanczos) to rasterize transparent colorkey (`#010203`) images.
- **Window Management**: Borderless `overrideredirect(True)` window with Win32 API calls (`SetWindowPos`, `SetWindowRgn`, `SetProcessDpiAwareness`, `WS_EX_TOOLWINDOW`).
- **Data & Polling**: Background daemon thread polling 9router's SQLite database (`usageDaily`, `usageHistory`, `requestDetails`, `providerConnections`) every 1.0s and HTTP health check every 3.0s.
- **State & Views**: Three view states (`min`: 320x42, `normal`: 520x136, `detailed`: 660x540) with dynamic shape transforms:
  - The Split Island: dual capsule / bubble ejection with ⚡ tok/s during active generation.
  - Magnetic Screen-Top Notch Docking: flattens top corners when docked near physical monitor top bezel.
- **Configuration & Integrations**: JSON persistence in `%LOCALAPPDATA%\hermes\dynamic_island_config.json`, Windows Startup registry integration (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`), 9router runner (`9router --no-browser`).

## 2. Components That Can Remain Unchanged (Reused in Backend)
- **Formatting Utilities**: `format_num()`, `format_time_ago()`, `format_time_left()`, `clean_provider_name()`, `clean_model_display_name()`.
- **9router SQLite Queries & Parsing**: Exact extraction logic for daily usage, request latency, prompt caching, token speeds (`latest_tps`), account quotas, model breakdown, and recent history.
- **9router Daemon Controls**: Health checking (`check_9router_health`), process runner (`run_9router`), and async quota fetching.
- **Windows Integration**: Windows Startup registry maintenance (`check_startup_registration`) and configuration file loading/saving (`load_config` / `save_config`).

## 3. Components That Must Be Rewritten
- **UI & Presentation Layer**: All Tkinter `Canvas`, PIL rasterization caches (`_capsule_cache`, `rounded_image`, `card_photos`), manual hit zones, and coordinate string text calls will be replaced by native **Qt Quick / QML** components.
- **Animation Loop**: The CPU-heavy Python 165Hz `tick_loop` is replaced by GPU-accelerated QML animations (`Behavior on width`, `NumberAnimation` with `Easing.OutBack` / `Easing.InOutQuad` spring approximation, `OpacityAnimator`).
- **Window Transparency**: Replaces Windows colorkey punching (`-transparentcolor #010203`) with native Qt transparent frameless window (`Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`, `color: "transparent"`).
- **High-DPI & Multi-Monitor**: Leverages Qt's built-in automatic Per-Monitor DPI scaling and `QScreen` geometries rather than manual GDI calls.

## 4. Proposed PySide6 / QML Architecture
```
app/
  __init__.py
  main.py                        # QGuiApplication, QQuickView / QQmlApplicationEngine setup
  backend/
    __init__.py
    hud_controller.py            # QObject subclass exposing properties, signals, and slots to QML
    data_service.py              # SQLite data fetching & 9router polling thread/timer
    models.py                    # Data classes and helper formatters
    system_integration.py        # Windows Startup registry, monitor detection, 9router runner
  ui/
    Main.qml                     # Root transparent window, drag handlers, view switcher
    components/
      IslandCapsule.qml          # Base capsule background with smooth corners & rim glow
      StatusDot.qml              # Anti-aliased pulsing status LED (green/orange/red)
      MinView.qml                # Compact pill with hover peek & Split Island bubble
      NormalView.qml             # Medium card with ticker & timeline buttons
      DetailedView.qml           # Full metrics grid, Account Manager carousel, breakdown & logs
      TimelineTabs.qml           # Segmented timeline pill selector
      PillButton.qml             # Reusable Apple-styled pill button
      CircleButton.qml           # Header circular icon button (9R, minimize, close)
    resources/
      fonts/                     # SF Pro Display otf fonts loaded via QFontDatabase
```

## 5. Risks and Compatibility Concerns
- **Window Transparency on Windows**: Qt Quick windows with `color: "transparent"` need proper surface format alpha buffers (`QQuickWindow.setDefaultAlphaBuffer(True)`).
- **Smooth Window Geometry Animation**: Animating root OS window bounds can hitch on Windows DWM. Best practice in Qt Quick: keep root window transparent with target dimensions or animate canvas and update window position cleanly, or use `QQuickWindow` with smooth property animations.
- **Click-through & Hit Testing**: Transparent areas outside the rounded pill must be click-through or transparent to user clicks. Qt handles transparent regions cleanly with mask or mouse transparent areas.

## 6. Migration Order
1. Build backend service modules (`data_service.py`, `models.py`, `system_integration.py`) reusing existing rock-solid business logic.
2. Build `hud_controller.py` with `@Property`, `@Signal`, and `@Slot` bindings.
3. Build QML components: `PillButton.qml`, `CircleButton.qml`, `StatusDot.qml`, `IslandCapsule.qml`.
4. Implement `MinView.qml` (with Split Island bubble and hover peek) and `NormalView.qml`.
5. Implement `DetailedView.qml` (metrics card, account manager carousel, models breakdown, API log).
6. Implement `Main.qml` root window with drag handling, docking notch mode, and animations.
7. Test and benchmark CPU, RAM, 165Hz fluidity, DPI, and shutdown against Tkinter baseline.
