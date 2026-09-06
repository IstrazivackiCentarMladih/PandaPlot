# Circuit Sketching Master Specification

**Parent Issue:** [#149 - Add electronics circuit sketching support (resistors, capacitors, diodes, coils)](https://github.com/Youth-Research-Center/PandaPlot/issues/149)
**Depends on:** [#148 - Add a sketching tab](https://github.com/Youth-Research-Center/PandaPlot/issues/148) (see `docs/specs/sketching/`)
**Milestone:** 11. Circuit Sketching
**Labels:** `area: chart-types`, `enhancement`

---

## Executive Summary

Issue #149 extends the Sketch item (#148) with a domain-specific component library for drawing simple electrical/electronics circuit diagrams — resistor, capacitor, inductor, diode, DC voltage source, and ground symbols, connected by wires, with value labels, rotate/flip, and (as a lower-priority stretch) basic measurement/simulation.

This spec corrects an earlier auto-generated proposal (PR #356), which invented its own model/GUI layout (`pandaplot/models/sketch/components/`, `pandaplot/services/sketch/`, a `QToolPalette` widget, `QRender`) that doesn't match anything in this codebase, and split the work into 6 sub-issues including a full persistence/export sub-issue for functionality the #148 foundation already provides generically. It also proposed a full nodal-analysis circuit simulator as same-priority, same-footing work alongside basic drawing — that's a substantial, higher-risk feature in its own right and shouldn't block or dilute the core drawing/labeling/export work most users of this issue actually want.

### Why this is only 4 sub-issues, not 6

The #148 foundation (see `docs/specs/sketching/05-export-and-extension-framework.md`, §3) was deliberately built with exactly one extension seam: a `type -> class` dict that `SketchElement.from_dict()` consults, populated by whatever modules register into it. That means:

- **Persistence is free.** `SketchDataManager` serializes any `SketchElement` subclass generically via `to_dict()`/`from_dict()`; it has no per-type logic to update. A new `CircuitComponentElement`/`WireElement` pair that follows the same `to_dict()`/`from_dict()` contract as the existing five element types round-trips through the same JSON-in-zip mechanism with zero sketch-core changes.
- **Image/SVG/PDF export is free.** `QGraphicsScene.render()` (Sub-Issue 5 of #148) draws whatever `QGraphicsItem`s are in the scene; it has no per-element-type branching to extend.

So there is no standalone "persistence and export" sub-issue here — each sub-issue below is responsible for making its own new element type(s) round-trip and render, verified by tests, using the same patterns #148 already established.

### Sub-Issue Index

| Sub-Issue | Title | Effort | Priority | Depends on |
|---|---|---|---|---|
| 1 | [Circuit component data model, symbols & palette](01-component-model-and-palette.md) | m | medium | #148 Sub-Issues 1, 2, 4 |
| 2 | [Wire routing & terminal snapping](02-wire-routing-and-snapping.md) | l | high | Sub-Issue 1 |
| 3 | [Component rotate/flip & value-label editing](03-transform-and-labeling.md) | m | medium | Sub-Issues 1, 2 |
| 4 | [Measurement probes & DC/AC simulation (stretch)](04-measurement-and-simulation.md) | l | low | Sub-Issues 1, 2, 3 |

Sub-Issues 1-3 deliver everything in #149's requirements except simulation, and are the ones worth scheduling first. Sub-Issue 4 is a distinct, higher-risk feature (a numeric solver, not a drawing feature) that should be scoped and possibly spiked separately before committing to it — see that spec's risk note.

---

## Traceability to Issue #149 Requirements

- **Palette of standard component symbols (resistor, capacitor, diode, inductor, wire, voltage source, ground):** Sub-Issue 1 (components), Sub-Issue 2 (wire).
- **Snap/connect via wires so circuits stay tidy:** Sub-Issue 2.
- **Label/annotate component values:** Sub-Issue 3.
- **Rotate/flip components:** Sub-Issue 3.
- **Persist as part of the project file, export as image:** Free, by construction — see above; verified in Sub-Issue 1/2's test plans.
- **Measuring devices and simulations, AC/DC:** Sub-Issue 4 (stretch, scoped down — see that spec).

## Architecture note: this stays inside the existing seam, not a new subsystem

Every new class in these specs is a `SketchElement` subclass (under `pandaplot/models/project/items/`, alongside the existing element types), a `QGraphicsItem` wrapper (under `pandaplot/gui/components/tabs/sketch/graphics_items/`), a `BaseTool` subclass (under `.../tools/`), and/or a `Command` subclass (under `pandaplot/commands/project/sketch/`) — the same four extension points #148 already defines. There is no new services layer, no new model package, and no new persistence code. Where a sub-issue below needs something #148 doesn't have (e.g. a snapping helper), it's added as a small module colocated with the rest of the sketch GUI code, not a new architectural layer.
