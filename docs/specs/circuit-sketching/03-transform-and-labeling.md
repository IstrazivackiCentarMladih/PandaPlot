# Sub-Issue 3 Design Specification: Component Rotate/Flip & Value-Label Editing

**Parent Issue:** [#149 - Add electronics circuit sketching support](https://github.com/Youth-Research-Center/PandaPlot/issues/149)
**Depends on:** Sub-Issue 1 (component model), Sub-Issue 2 (wires, so transforms can keep them attached)
**Milestone:** 11. Circuit Sketching
**Labels:** `area: chart-types`, `effort: m`, `enhancement`, `priority: medium`

---

## 1. Goal

Let users rotate components in 90° steps, flip them horizontally/vertically, and edit each component's designator/value label in place — while keeping any connected wires attached and label text upright.

---

## 2. Rotate/Flip

No new model fields beyond what Sub-Issue 1 already added (`rotation` from the base `SketchElement`, `flip_horizontal`/`flip_vertical` from `CircuitComponentElement`). This sub-issue is UI + commands:

- **Hotkeys**, active when the current selection is one or more `CircuitComponentElement`s (checked in the same place the base `SelectTool` already checks selection type for the resize-handle logic in #148 Sub-Issue 2 — no new tool class needed, just a conditional key-binding branch there):
  - `R` — rotate 90° clockwise (`rotation = (rotation + 90) % 360`).
  - `Shift+R` — rotate 90° counter-clockwise.
  - `H` — toggle `flip_horizontal`.
  - `V` — toggle `flip_vertical`.
- `TransformCircuitComponentCommand(component_id, rotation, flip_horizontal, flip_vertical)`: undoable, analogous to #148 Sub-Issue 3's `UpdateElementStyleCommand` (stores old values, `execute()`/`undo()` swap them). For a selection with attached wires, compose with `UpdateWireWaypointsCommand` per affected wire via `CompositeCommand` — reusing exactly the pattern Sub-Issue 2 already establishes for moves, not a separate mechanism for rotation.
- Multi-select: applying rotate/flip to a multi-component selection transforms each component in place around its own anchor (not around the selection's collective center) — simpler to reason about and matches how a schematic symbol's own orientation is what rotate/flip means for it.

## 3. Value-Label Editing

Reuses #148 Sub-Issue 3's property inspector rather than adding a second panel:

```
pandaplot/gui/components/tabs/sketch/
└── sketch_property_bar.py   # extended, not a new file
```

- When the current selection is one or more `CircuitComponentElement`s, the property bar shows two additional text fields: **Designator** and **Value**, alongside the existing stroke/fill controls (which still apply — a resistor symbol's outline is still a stroke).
- Editing either field with a single component selected updates that field directly. With a multi-component selection of mixed values, both fields show the base spec's existing "Mixed" placeholder convention rather than a bespoke one for circuits.
- `UpdateComponentLabelCommand(component_ids, designator=None, value=None)`: same shape as #148's `UpdateElementStyleCommand` (only touches the fields that were actually provided, undoable, returns `NOOP` if nothing changed) — not a new command pattern.
- No in-place double-click canvas text editing in this pass (the original proposal's `QGraphicsTextItem` double-click editor) — the property bar already covers this need and adding a second editing path is unnecessary duplication for a first version. Revisit only if user feedback asks for it.

---

## 4. Verification & Testing Plan

1. **Command tests (`tests/commands/project/sketch/test_circuit_transform_and_label_commands.py`)**:
   - `TransformCircuitComponentCommand` execute/undo/redo for rotate and each flip axis, asserting `CommandResult`.
   - Rotating/flipping a component with an attached wire updates that wire's waypoints in the same undo step.
   - `UpdateComponentLabelCommand` returns `NOOP` when designator/value are unchanged.
2. **GUI tests (`tests/gui/sketch/test_circuit_transform_and_labels.py`, `QT_QPA_PLATFORM=offscreen`)**:
   - `R`/`Shift+R`/`H`/`V` hotkeys apply the expected transform to a selected component and are undoable.
   - Label text stays visually upright at `rotation=90` and `rotation=270` (render and check the label sub-item's effective transform, not just the model field).
   - Property bar shows designator/value fields only when a circuit component is selected, and shows "Mixed" for a heterogeneous multi-select.
