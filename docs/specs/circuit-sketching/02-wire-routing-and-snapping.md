# Sub-Issue 2 Design Specification: Wire Routing & Terminal Snapping

**Parent Issue:** [#149 - Add electronics circuit sketching support](https://github.com/Youth-Research-Center/PandaPlot/issues/149)
**Depends on:** Sub-Issue 1 (component model & terminals)
**Milestone:** 11. Circuit Sketching
**Labels:** `area: chart-types`, `effort: l`, `enhancement`, `priority: high`

---

## 1. Goal

Let users connect component terminals with wires that snap into place and stay attached when a component moves, so circuits stay visually tidy without manual redrawing.

---

## 2. Model

```
pandaplot/models/project/items/sketch_elements/
└── wire_element.py   # WireElement
```

### 2.1 `WireElement(SketchElement)`

- `waypoints: list[tuple[float, float]]` — ordered list of points from start to end, in canvas coordinates (not relative to a local anchor — a wire has no single natural anchor the way a shape does). `x`/`y` on the base class are unused for wires (kept `0.0`); this is an acceptable inconsistency given `SketchElement.from_dict()` doesn't require every field to be meaningful for every subtype, same as `FreehandElement` already ignores rotation in practice.
- `start_ref: TerminalRef | None`, `end_ref: TerminalRef | None`, where `TerminalRef = tuple[element_id: str, terminal_id: str]` — `None` for a wire endpoint left floating (not connected to anything), which is allowed; users can draw a wire before placing the component it'll eventually connect to.

### 2.2 Keep it a flat element list, not a graph

The original proposal's `CircuitGraph` (a separate topological graph of nodes/edges mirroring the elements) is redundant for this sub-issue — nothing here needs graph algorithms yet. `start_ref`/`end_ref` on each `WireElement` is enough to answer "what's connected to what" by scanning the layer's element list. Build `CircuitGraph` only when Sub-Issue 4 (simulation) actually needs a solvable topology — deferring it there means it's designed against real solver requirements instead of guessed now. Do not add it in this sub-issue.

---

## 3. Snapping (`pandaplot/gui/components/tabs/sketch/tools/`)

```
tools/
└── wire_tool.py   # BaseTool subclass
```

No separate "service layer" — snapping is a small pure function, not a stateful service:

```python
def find_snap_terminal(point: tuple[float, float], elements: list[SketchElement], radius_px: float = 10.0) -> TerminalRef | None:
    ...
```

- `WireTool`: press near a terminal (within `radius_px`, in view coordinates so snap distance doesn't change with zoom) starts a wire from that terminal; drag adds orthogonal waypoints (simple Manhattan elbow — horizontal-then-vertical from the last point to the cursor, recomputed live, not full pathfinding/obstacle avoidance); release near another terminal completes the connection via `start_ref`/`end_ref`, release elsewhere leaves that endpoint floating. This is deliberately simpler than the original proposal's "A* / minimum-bend routing around obstacles" — obstacle-avoiding autorouting is a substantial feature on its own and isn't needed for #149's stated requirement ("stay tidy as they're built"); a live-updating elbow is enough for that.
- Terminal highlight: when `WireTool` is active and the cursor is within `radius_px` of a terminal, render a small highlight marker at that terminal (a child `QGraphicsEllipseItem` on the relevant `CircuitComponentGraphicsItem`, toggled via a property rather than a new overlay item type).

---

## 4. Keeping wires attached when a component moves

- `CircuitComponentGraphicsItem.itemChange()` (Qt's standard hook for position-change notifications) triggers a scene-level callback that re-derives affected wires' endpoint waypoints from the moved component's new `terminal_world_pos()` (Sub-Issue 1, §2.1) — this only touches the *view-side* waypoint recompute for live dragging; it doesn't mutate the model per-frame.
- On mouse release (drag finished), commit the final position via a `MoveComponentWithWiresCommand(component_id, new_x, new_y, updated_wire_waypoints)` that wraps the component's move and every attached wire's waypoint update as one undo/redo unit, built with `CompositeCommand` (`pandaplot/commands/composite_command.py`, from #333) over the existing single-element move command plus one `UpdateWireWaypointsCommand` per affected wire — not a new bespoke undo mechanism.
- `ConnectWireCommand(wire_id, end: Literal["start","end"], ref: TerminalRef)` / `DisconnectWireCommand(wire_id, end)`: undoable, used when the user finishes or explicitly detaches a wire endpoint.

---

## 5. Verification & Testing Plan

1. **Model tests (`tests/models/project/items/test_wire_element.py`)**: `to_dict()`/`from_dict()` round-trip including floating (`None`) endpoints.
2. **Snapping unit test (`tests/gui/sketch/test_wire_snapping.py`)**: `find_snap_terminal` returns the nearest terminal within radius and `None` outside it, across a small synthetic set of placed components — no Qt event loop needed for this part.
3. **GUI interaction tests (`tests/gui/sketch/test_wire_tool.py`, `QT_QPA_PLATFORM=offscreen`)**:
   - Drag from one terminal to another creates a connected `WireElement` via the tool's commands.
   - Moving a connected component updates the wire's waypoints and the change is a single undo step (via `CompositeCommand`).
   - Disconnecting a wire endpoint leaves it floating without deleting the wire.
