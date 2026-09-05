# Sketching Tab Architecture & Sub-Issues Master Specification

**Parent Issue:** [#148 - Add a sketching tab (freehand/shape drawing canvas item)](https://github.com/Youth-Research-Center/PandaPlot/issues/148)
**Milestone:** Backlog
**Labels:** `area: chart-types`, `effort: l`, `enhancement`, `priority: medium`

---

## Executive Summary

PandaPlot currently supports Chart, Dataset, Note, Image, and Folder items within its hierarchical project structure. Issue #148 introduces a dedicated **Sketching Tab** (`Sketch` item) — a vector drawing canvas operating alongside existing tabs, serving as a canvas for freehand drawing, geometric shapes, text labels, and layered diagrams.

To ensure modularity, high code quality, testability, and incremental delivery, Issue #148 is decomposed into **5 sub-issues**, all under the **Backlog** milestone.

---

## Sub-Issue Index

| Issue # | Title | Effort | Priority | Key Deliverables |
|---------|-------|--------|----------|------------------|
| **Sub-Issue 1** | [[Sketch Tab] Sketch Data Model, Layer Architecture, and Project Persistence](01-data-model-and-persistence.md) | `effort: m` | `priority: medium` | `Sketch` Item model, `SketchLayer`, element primitives (`Freehand`, `Line`, `Rectangle`, `Ellipse`, `Text`), `SketchDataManager` (`sketch_{id}.json` serialization). |
| **Sub-Issue 2** | [[Sketch Tab] Canvas Viewport, Interactive Tools, and Selection/Manipulation](02-canvas-and-drawing-tools.md) | `effort: m` | `priority: medium` | `QGraphicsScene`/`QGraphicsView` canvas, tool state machine, freehand/shape/text tools, selection handles, resize/move/delete, pan & zoom. |
| **Sub-Issue 3** | [[Sketch Tab] Element Styling Controls, Property Inspector, and Commands](03-styling-and-property-inspector.md) | `effort: s` | `priority: medium` | Property inspector toolbar, stroke/fill/line-width/font options, live styling, undoable/redoable commands for element mutations. |
| **Sub-Issue 4** | [[Sketch Tab] Layer Management UI, Tab Editor, and Project Tree Integration](04-layer-management-and-gui-integration.md) | `effort: m` | `priority: medium` | `SketchTab` view, project tree context menu & icons, `LayerManagerPanel` (add/remove/reorder layers, visibility & lock toggles). |
| **Sub-Issue 5** | [[Sketch Tab] Image Export and Domain Extension Framework Foundation](05-export-and-extension-framework.md) | `effort: s` | `priority: medium` | Export to PNG/SVG/PDF/JPEG, resolution/transparency controls, `SketchExtension` & component registry for domain-specific follow-ups (e.g. circuit sketching). |

---

## High-Level Architecture

```
                                  ┌────────────────────────┐
                                  │      Project Tree      │
                                  └───────────┬────────────┘
                                              │ Creates/Opens
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                       SketchTab                                        │
│  ┌───────────────────────┐  ┌───────────────────────────────────┐  ┌────────────────┐  │
│  │    Drawing Toolbar    │  │       SketchCanvas (View/Scene)   │  │ Layer Manager  │  │
│  │ (Pen, Line, Rect,...) │  │  ┌─────────────────────────────┐  │  │ (Layers List,  │  │
│  └───────────┬───────────┘  │  │ Layer 2 (Active/Visible)    │  │  │ Visibility,    │  │
│              │ Active Tool  │  │  ├─ TextElement             │  │  │ Lock, Reorder) │  │
│              ▼              │  └─────────────────────────────┘  │  └───────┬────────┘  │
│  ┌───────────────────────┐  │  ┌─────────────────────────────┐  │          │ Sync      │
│  │  Property Inspector   │  │  │ Layer 1 (Locked/Visible)    │  │  ◄───────┘           │
│  │ (Color, Width, Font)  │  │  │  ├─ FreehandElement         │  │                      │
│  └───────────────────────┘  │  │  └─ RectangleElement        │  │                      │
│                             │  └─────────────────────────────┘  │                      │
│                             └─────────────────┬─────────────────┘                      │
└───────────────────────────────────────────────┼────────────────────────────────────────┘
                                                │ Persists to
                                                ▼
                                    ┌───────────────────────┐
                                    │   SketchDataManager   │
                                    │  (`sketch_{id}.json`) │
                                    └───────────────────────┘
```

---

## Traceability to Issue #148 Requirements

- **New "Sketch" item type in project tree with own tab/editor:** Handled by Sub-Issues 1 & 4.
- **Basic drawing tools (freehand pen, straight lines, basic shapes, text labels):** Handled by Sub-Issue 2.
- **Selection, move, resize, delete of drawn elements:** Handled by Sub-Issue 2.
- **Color/line-width/style controls for drawn elements:** Handled by Sub-Issue 3.
- **Persist sketches as part of project file:** Handled by Sub-Issue 1.
- **Export sketch as an image:** Handled by Sub-Issue 5.
- **Layers support:** Handled by Sub-Issues 1 & 4.
- **Foundation for structured-drawing features (electronics circuit follow-up):** Handled by Sub-Issue 5.
