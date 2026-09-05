# Sub-Issue 3 Design Specification: Element Styling Controls, Property Inspector, and Commands

**Parent Issue:** [#148 - Add a sketching tab (freehand/shape drawing canvas item)](https://github.com/Youth-Research-Center/PandaPlot/issues/148)
**Milestone:** Backlog
**Labels:** `area: chart-types`, `effort: s`, `enhancement`, `priority: medium`

---

## 1. Goal & Objectives

Provide UI components for styling controls (stroke color, fill color/alpha, line width, line pattern style, font attributes), sync property inspector state bidirectionally with canvas selection, and execute styling changes via undoable/redoable commands.

---

## 2. UI Component Design

```
pandaplot/gui/components/tabs/sketch/
├── sketch_property_bar.py      # Top/Side property inspector toolbar
└── commands/
    ├── add_element_command.py
    ├── update_style_command.py
    ├── transform_element_command.py
    └── delete_element_command.py
```

### 2.1 Property Inspector Controls (`sketch_property_bar.py`)

- **Stroke Color Picker**: Color swatch button (`ColorSwatchRow` / `QColorDialog`) with hex display.
- **Fill Color & Opacity**: Color swatch button + opacity slider (`0% - 100%`) or `"None"` (transparent).
- **Line Width**: SpinBox / Slider (`0.5 pt` to `50.0 pt`).
- **Line Style**: Dropdown (`Solid`, `Dashed`, `Dotted`, `Dash-Dot`).
- **Font Controls** (active when text element or text tool selected):
  - Font Family Dropdown (`FontFamilyOptions`).
  - Font Size SpinBox (`6 pt` to `144 pt`).
  - Bold (`B`) / Italic (`I`) Toggle Buttons.
  - Alignment Segmented Control (`Left`, `Center`, `Right`).

---

## 3. Dynamic Synchronization & Default Properties

1. **Default Properties for New Elements**:
   - Changing property controls when **no element is selected** updates the active tool's default style.
   - Newly created elements automatically inherit these default styles.
2. **Selection Inspection & Live Update**:
   - Selecting element(s) populates property controls with the selection's attributes.
   - If multiple elements are selected with heterogeneous values, controls display `"Mixed"`.
   - Modifying a control with an active selection immediately updates all selected elements.

---

## 4. Undo/Redo Command Architecture

Integrated into PandaPlot's `CommandExecutor` (`pandaplot/commands/`):

- **`AddSketchElementCommand(sketch, layer_id, element)`**:
  - `execute()`: Appends element to layer.
  - `undo()`: Removes element from layer.
- **`UpdateElementStyleCommand(sketch, element_ids, property_dict)`**:
  - Stores old property values per element ID.
  - `execute()`: Applies `property_dict` to elements.
  - `undo()`: Restores old property values.
- **`DeleteSketchElementsCommand(sketch, layer_id, element_ids)`**:
  - `execute()`: Removes specified elements.
  - `undo()`: Restores elements back to layer in original order.

---

## 5. Verification & Testing Plan

1. **Unit Tests (`tests/commands/test_sketch_commands.py`)**:
   - Test `execute()`, `undo()`, and `redo()` for style updates and element additions/deletions.
2. **GUI Interaction Tests (`tests/gui/sketch/test_sketch_property_bar.py`)**:
   - Verify changing color picker updates selected element model.
   - Verify selecting an element updates property bar controls correctly.
