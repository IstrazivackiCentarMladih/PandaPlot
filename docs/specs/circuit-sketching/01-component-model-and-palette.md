# Sub-Issue 1 Design Specification: Circuit Component Data Model, Symbols & Palette

**Parent Issue:** [#149 - Add electronics circuit sketching support](https://github.com/Youth-Research-Center/PandaPlot/issues/149)
**Depends on:** #148 Sub-Issue 1 (data model/persistence), Sub-Issue 2 (canvas/tools), Sub-Issue 4 (tab/tree integration)
**Milestone:** 11. Circuit Sketching
**Labels:** `area: chart-types`, `effort: m`, `enhancement`, `priority: medium`

---

## 1. Goal

Add a `CircuitComponentElement` type covering the six symbols #149 asks for (resistor, capacitor, inductor, diode, DC voltage source, ground), register it into the shared element-type dict from #148, and add a palette panel + placement tool so components can be dropped onto a `Sketch` canvas.

---

## 2. Model (`pandaplot/models/project/items/`)

Follow the existing `sketch.py` element layout exactly — a new sibling module, not a new package tree:

```
pandaplot/models/project/items/
└── sketch_elements/           # (or wherever #148 lands the 5 base element classes)
    └── circuit_component_element.py   # CircuitComponentElement, ComponentType, Terminal
```

### 2.1 `CircuitComponentElement(SketchElement)`

Reuses every base `SketchElement` field (`id`, `type`, `x`, `y`, `rotation`, `stroke_color`, `stroke_width`, `stroke_style`, `fill_color`) — a circuit symbol is drawn with the same stroke it would use as a generic shape. Adds:

- `component_type: str` — one of `"resistor"`, `"capacitor"`, `"inductor"`, `"diode"`, `"voltage_source"`, `"ground"`.
- `terminals: list[Terminal]` — fixed per `component_type` (not user-editable), each `Terminal(id: str, dx: float, dy: float)` in the symbol's local, unrotated coordinate space (offset from the element's `(x, y)` anchor). Two terminals for resistor/capacitor/inductor/diode/voltage_source, one for ground.
- `flip_horizontal: bool`, `flip_vertical: bool` (default `False`) — schematic symbols are only ever axis-aligned, so flip is a boolean pair here rather than a general affine transform; see Sub-Issue 3 for how these combine with the base `rotation` field.
- `designator: str` (e.g. `"R1"`, default `""`), `value: str` (e.g. `"10k"`, `"100n"`, default `""`), `label_visible: bool` (default `True`).

No separate `ComponentAnnotation` sub-object — keeping designator/value as flat fields matches how `TextElement`, `RectangleElement`, etc. are already flat, and there's exactly one label per component, not an open-ended list.

Terminal *world* position for wire-snapping purposes (Sub-Issue 2) is derived, never stored: rotate `(dx, dy)` by `rotation` (after applying the flip signs), then translate by `(x, y)`. Keep this derivation as a single method on `CircuitComponentElement`, e.g. `terminal_world_pos(terminal_id) -> tuple[float, float]`, so Sub-Issue 2's snapping code and the `QGraphicsItem` wrapper compute it identically.

### 2.2 Registration into the shared seam

In `circuit_component_element.py`:

```python
from pandaplot.models.project.items.sketch_elements.sketch_element import ELEMENT_TYPES

ELEMENT_TYPES["circuit_component"] = CircuitComponentElement
```

(module name/import path to match wherever #148 Sub-Issue 1 actually places the `type -> class` dict named in its spec — confirm the exact name/location when that sub-issue lands, since it's speculative until then.) This is the *only* change needed in shared sketch code — no edits to `SketchElement.from_dict()`, `SketchDataManager`, or the export path.

---

## 3. Symbol Rendering (`pandaplot/gui/components/tabs/sketch/graphics_items/`)

```
graphics_items/
└── circuit_component_item.py   # QGraphicsItem subclass, one per component_type's QPainterPath
```

- One `CircuitComponentGraphicsItem(QGraphicsItem)` whose `paint()` dispatches on `component_type` to build the right `QPainterPath` (zig-zag for resistor, parallel plates for capacitor, coil arcs for inductor, triangle+bar for diode, circle+/- for voltage source, ground hatching), each drawn in a fixed local bounding box (e.g. 40x20 units) so terminal offsets in §2.1 are consistent constants per type.
- Applies `flip_horizontal`/`flip_vertical` via `QTransform.scale(-1, 1)` / `scale(1, -1)` composed before `rotation`, then renders the designator/value label (from Sub-Issue 3) as a child `QGraphicsSimpleTextItem` that ignores the parent's rotation/flip transform (`ItemIgnoresTransformations` is too aggressive — instead counter-rotate the label's own transform) so text stays upright, matching the requirement called out in the original proposal.
- No LaTeX/MathText rendering — that's speculative for a first pass; plain Unicode (`Ω`, `µ`) in the value string is enough, consistent with how the rest of the sketch tab's `TextElement` renders (no math support there either).

---

## 4. Palette Panel & Placement Tool

```
pandaplot/gui/components/tabs/sketch/
├── circuit_palette_panel.py   # Sidebar listing the 6 symbols (QListWidget with icons is enough — no new widget class needed)
└── tools/
    └── circuit_component_tool.py   # BaseTool subclass: click-to-place a CircuitComponentElement of the selected type
```

- `CircuitPalettePanel` is a collapsible sidebar akin to #148 Sub-Issue 4's `LayerManagerPanel`, shown only when a circuit-capable palette is registered (i.e., always, once this sub-issue lands — no feature flag needed).
- Selecting a palette entry switches `ToolManager`'s active tool to `CircuitComponentTool(component_type)` (one tool class parameterized by type, not six). Click places the component at the click point with default `rotation=0`, `flip_*=False`, empty `designator`/`value`, via `AddSketchElementCommand` — reusing #148 Sub-Issue 3's command, not a new one.

---

## 5. Verification & Testing Plan

1. **Model tests (`tests/models/project/items/test_circuit_component_element.py`)**:
   - `to_dict()`/`from_dict()` round-trip for all 6 `component_type` values, including `terminals`, `flip_horizontal`, `flip_vertical`, `designator`, `value`.
   - `terminal_world_pos()` returns correct coordinates for at least one rotated + flipped case (not just the identity case), since sign errors here are exactly the kind of bug that's invisible until Sub-Issue 2's wires visibly detach on rotate.
2. **Registration test**: confirm `"circuit_component"` resolves via the shared element-type dict without touching any of the 5 existing element modules.
3. **Persistence round-trip**: save a `Sketch` containing a `CircuitComponentElement` through a real `ZipFile` via `SketchDataManager` (same pattern as #148 Sub-Issue 1's test) and confirm deep equality after load — this is the test that proves the "persistence is free" claim in the overview, so don't skip it.
4. **Export smoke test**: render a `Sketch` containing one of each `component_type` to a PNG via the existing export path (#148 Sub-Issue 5) and confirm it doesn't raise — this is the equivalent proof for export.
5. **GUI tests (`tests/gui/sketch/test_circuit_palette.py`)**:
   - Selecting a palette entry then clicking the canvas creates the right `component_type` at the click point via `AddSketchElementCommand`.
