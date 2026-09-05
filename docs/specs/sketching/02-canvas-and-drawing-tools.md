# Sub-Issue 2 Design Specification: Canvas Viewport, Interactive Tools, and Selection/Manipulation

**Parent Issue:** [#148 - Add a sketching tab (freehand/shape drawing canvas item)](https://github.com/Youth-Research-Center/PandaPlot/issues/148)
**Milestone:** Backlog
**Labels:** `area: chart-types`, `effort: m`, `enhancement`, `priority: medium`

---

## 1. Goal & Objectives

Develop the interactive graphics canvas component (`SketchCanvas`) using Qt's `QGraphicsScene` / `QGraphicsView` framework, alongside a tool controller state machine and interactive drawing tools (Freehand Pen, Line, Rectangle, Ellipse, Text Label) with selection, movement, resizing, deletion, and viewport navigation (pan/zoom).

---

## 2. Architecture & Components

```
pandaplot/gui/components/tabs/sketch/
├── sketch_canvas.py          # Custom QGraphicsView & QGraphicsScene wrapper
├── tools/
│   ├── tool_manager.py       # Active tool state controller
│   ├── base_tool.py          # Abstract Tool base class
│   ├── select_tool.py        # Selection & transform tool
│   ├── freehand_tool.py      # Freehand path drawing tool
│   ├── line_tool.py          # Straight line tool
│   ├── shape_tools.py        # Rectangle & Ellipse drawing tools
│   └── text_tool.py          # Interactive text label placement tool
└── graphics_items/
    ├── base_graphics_item.py # Maps SketchElement <-> QGraphicsItem
    ├── freehand_item.py
    ├── line_item.py
    ├── shape_items.py
    └── text_item.py
```

---

## 3. Tool State Machine & Interaction Behaviors

### 3.1 Tool Manager (`tool_manager.py`)
- Maintains current active tool mode: `SELECT`, `FREEHAND`, `LINE`, `RECTANGLE`, `ELLIPSE`, `TEXT`.
- Routes mouse events (`mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent`, `keyPressEvent`) from `SketchCanvas` to active tool handler.

### 3.2 Tool Mechanics

| Tool Mode | Mouse Down | Mouse Drag | Mouse Up |
|-----------|------------|------------|----------|
| **`SelectTool`** | Hits element -> selects; Hits empty canvas -> starts Rubberband Selection box. | Moves selected element(s) or resizes via handle; Updates rubberband box. | Finalizes element positions/dimensions in model. |
| **`FreehandTool`** | Starts new `FreehandElement` path at press point. | Appends points to active path, updating preview curve. | Finalizes path, adds `FreehandElement` to active layer in model. |
| **`LineTool`** | Sets line start point `(x1, y1)`. | Updates end point `(x2, y2)`, rendering dynamic preview line. | Creates `LineElement` in active layer. |
| **`RectangleTool`** | Sets top-left anchor `(x, y)`. | Updates width/height based on current drag position. | Creates `RectangleElement` in active layer. |
| **`EllipseTool`** | Sets top-left / center anchor. | Updates bounding radiuses `rx, ry`. | Creates `EllipseElement` in active layer. |
| **`TextTool`** | Clicking canvas opens inline `QLineEdit` or text input dialog. | N/A | Submitting text creates `TextElement` at click coordinates. |

---

## 4. Canvas Viewport Operations

### 4.1 Selection Handles & Bounding Box
- Custom selection overlay items (`QGraphicsItem` bounding box with 8 handle points: N, NE, E, SE, S, SW, W, NW).
- Dragging handles resizes element while preserving aspect ratio if Shift is held.
- Pressing `Delete` or `Backspace` deletes selected elements from active layer.

### 4.2 Viewport Navigation (Pan & Zoom)
- **Zooming**: `Ctrl + Mouse Wheel` or pinch gesture scales canvas viewport (`10%` to `1000%`).
- **Panning**: Holding `Spacebar + Left Click Drag` or `Middle Mouse Button Drag` pans viewport.

---

## 5. Verification & Testing Plan

1. **GUI Headless Tests (`tests/gui/sketch/test_sketch_canvas.py`)**:
   - Run with `QT_QPA_PLATFORM=offscreen`.
   - Test item creation via tool event triggers (press -> drag -> release).
   - Test selection handle bounds calculation.
   - Verify non-active / locked layers ignore selection and pointer interactions.
2. **Interactive Event Tests**:
   - Verify key press deletion (`Delete` key) removes items from scene and model.
