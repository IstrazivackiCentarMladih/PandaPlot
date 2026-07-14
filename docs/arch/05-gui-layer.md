# GUI Layer

## Overview

The GUI is built with PySide6 (Qt6). All widgets extend `WidgetExtension`, which provides a standardized lifecycle and automatic EventBus subscription management.

## Main Window (`gui/main_window.py`)

```
PandaMainWindow (QMainWindow)
├── MenuBar                    # File, Edit, View, Tools, Help menus
├── QSplitter (horizontal)
│   ├── CollapsibleSidebar     # Left panel with icon tabs
│   └── TabContainer           # Right panel workspace
└── StatusBar
```

## WidgetExtension (`gui/core/widget_extension.py`)

Base class for all GUI components. Defines the initialization lifecycle:

```
_initialize()
  ├── _init_ui()                # Build widget tree (abstract, override this)
  ├── _apply_theme()            # Apply current theme colors/fonts
  └── setup_event_subscriptions()  # Register EventBus callbacks

# On destroy:
  └── Auto-unsubscribes all registered event callbacks
```

## CollapsibleSidebar (`gui/components/sidebar/`)

Icon-based left panel switcher. Each icon maps to a panel:

| Icon | Panel | Shown when |
|------|-------|-----------|
| Project tree | `ProjectViewPanel` | Always |
| Dataset info | `DatasetPanel` | Dataset item selected |
| Chart props | `ChartPropertiesPanel` | Chart item selected |
| Analysis | `AnalysisPanel` | Dataset or chart active |
| Curve fit | `FitPanel` | Chart with series active |
| Transform | `TransformPanel` | Dataset active |

`ConditionalPanelManager` listens to `UIEvents` and `ProjectEvents` to show/hide the correct panel automatically.

### ProjectViewPanel

Hierarchical tree view of all project items. Subscribes to:
- `project.item_added` → inserts tree node
- `project.item_removed` → removes tree node
- `project.item_renamed` → updates label

Double-clicking an item opens it in a tab.

## TabContainer (`gui/components/tabs/`)

Manages the workspace tabbed area:

```
TabContainer
├── CustomTabWidget             # QTabWidget with close buttons
├── WelcomeTab                  # Shown when no project is open
├── DatasetTab                  # Spreadsheet editor for a Dataset
├── ChartTab                    # Matplotlib chart canvas
└── NoteTab                     # Markdown note editor
```

### DatasetTab

- Displays `pandas.DataFrame` in a `QTableView` with lazy loading for large datasets
- Subscribes to all `DatasetOperationEvents` to refresh individual cells/columns rather than rebuilding the full table
- Toolbar actions map directly to dataset commands (add/delete rows, add/delete columns, transform)

### ChartTab

- Embeds a `FigureCanvasQTAgg` (matplotlib → Qt bridge)
- `ChartRenderEngine` converts the `Chart` model into a `matplotlib.Figure`:
  1. Create figure and axes
  2. For each `DataSeries`: fetch columns from Dataset, call `ax.plot()` / `ax.scatter()` / etc.
  3. For each `FitData`: evaluate fit function over x range, overlay curve
  4. Apply `ChartConfiguration` (title, labels, legend, grid)
- Subscribes to `ChartEvents` to re-render on any chart change

### NoteTab

- Plain text editor with optional markdown preview split
- Subscribes to `NoteEvents` to sync content

## UIController (`gui/controllers/`)

Facade over all Qt dialog types. GUI components call `UIController` instead of constructing dialogs directly:

```python
# File dialogs
path = ui_controller.show_open_project_dialog()
path = ui_controller.show_save_project_dialog()
path = ui_controller.show_import_csv_dialog()

# Message dialogs
ui_controller.show_error("Something went wrong", detail)
ui_controller.show_warning("Are you sure?")
confirmed = ui_controller.show_question("Save before closing?")

# Input dialogs
name = ui_controller.show_text_input("Enter column name")
value = ui_controller.show_number_input("Enter threshold", default=0.0)
```

The `UIController` stores the `parent_widget` reference so all dialogs are properly modal.

## Theme System (`services/theme/`)

`ThemeManager` supports light and dark themes:

1. `ThemeManager.set_theme(ThemeMode.DARK)` → persists preference, emits `ThemeEvents.THEME_CHANGED`
2. All `WidgetExtension` subclasses receive the event and call `_apply_theme()`
3. `_apply_theme()` reads the current theme from `ThemeManager` and updates Qt stylesheets

## Background Tasks (`services/qtasks/`)

Long-running operations (large CSV imports, analysis on big datasets) run via `TaskScheduler`:

```
TaskScheduler
└── QThreadPool
    └── Worker (QRunnable)
        ├── run()             # Executes the callable on a thread
        ├── signals.result    # Emitted on success
        └── signals.error     # Emitted on exception
```

GUI components connect to worker signals to show progress or handle completion without blocking the Qt event loop.
