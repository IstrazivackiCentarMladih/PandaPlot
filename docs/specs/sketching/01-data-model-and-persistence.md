# Sub-Issue 1 Design Specification: Sketch Data Model, Layer Architecture, and Project Persistence

**Parent Issue:** [#148 - Add a sketching tab (freehand/shape drawing canvas item)](https://github.com/Youth-Research-Center/PandaPlot/issues/148)
**Milestone:** Backlog
**Labels:** `area: chart-types`, `effort: m`, `enhancement`, `priority: medium`

---

## 1. Goal & Objectives

Establish the foundational data domain model for the `Sketch` item, its layer hierarchy, element primitives, and its serialization/deserialization logic for persistence inside `.pplot` project zip archives.

---

## 2. Model Design Architecture

### 2.1 Class Hierarchy

```
pandaplot/models/project/items/
├── sketch.py
│   ├── Sketch (inherits Item)
│   ├── SketchLayer
│   └── elements/
│       ├── sketch_element.py (Base abstract class)
│       ├── freehand_element.py
│       ├── line_element.py
│       ├── rectangle_element.py
│       ├── ellipse_element.py
│       └── text_element.py
```

### 2.2 Classes & Attributes

#### `Sketch` (`pandaplot/models/project/items/sketch.py`)
Inherits from `Item` (`pandaplot/models/project/items/item.py`).
- `item_type`: `"sketch"`
- `layers: list[SketchLayer]`: Ordered list of layers (index 0 is bottom-most, last index is top-most).
- `active_layer_id: str`: ID of currently active drawing layer.
- `canvas_width: float` / `canvas_height: float`: Canvas dimensions (default: 1920x1080 or responsive bounds).
- `background_color: str`: Hex background color (default: `"#FFFFFF"`).

#### `SketchLayer`
- `id: str`: UUID identifier.
- `name: str`: Layer name (e.g. `"Layer 1"`).
- `visible: bool`: Visibility flag (default: `True`).
- `locked: bool`: Lock flag preventing modifications (default: `False`).
- `opacity: float`: Layer opacity between `0.0` and `1.0` (default: `1.0`).
- `elements: list[SketchElement]`: Ordered list of elements within this layer.

#### `SketchElement` (Abstract Base Class)
- `id: str`: UUID identifier.
- `type: str`: Element discriminator string (`"freehand"`, `"line"`, `"rectangle"`, `"ellipse"`, `"text"`).
- `x: float`, `y: float`: Anchor position in canvas coordinate space.
- `rotation: float`: Rotation angle in degrees.
- `stroke_color: str`: Stroke color in hex/RGBA string (e.g. `"#000000"`).
- `stroke_width: float`: Stroke line width (default: `2.0`).
- `stroke_style: str`: `"solid"`, `"dashed"`, `"dotted"`, `"dash_dot"`.
- `fill_color: str`: Fill color in hex/RGBA string or `"none"`.

#### Concrete Element Types

1. **`FreehandElement`**:
   - `points: list[tuple[float, float]]`: List of `(x, y)` relative or canvas coordinates forming the path.

2. **`LineElement`**:
   - `x1: float, y1: float`: Start coordinate.
   - `x2: float, y2: float`: End coordinate.

3. **`RectangleElement`**:
   - `width: float`: Width of rectangle.
   - `height: float`: Height of rectangle.
   - `corner_radius: float`: Radius for rounded corners (default `0.0`).

4. **`EllipseElement`**:
   - `rx: float`: X-radius or width.
   - `ry: float`: Y-radius or height.

5. **`TextElement`**:
   - `text: str`: Text content string.
   - `font_family: str`: Font family (default: `"Sans-Serif"`).
   - `font_size: int`: Font size in points (default: `14`).
   - `is_bold: bool`, `is_italic: bool`: Formatting flags.
   - `alignment: str`: `"left"`, `"center"`, `"right"`.

---

## 3. Storage & Persistence (`pandaplot/storage/sketch_data_manager.py`)

### 3.1 Serialization Format (`sketch_{id}.json`)

Each `Sketch` item is saved as a JSON file inside the `.pplot` archive under the filename `sketch_{id}.json`.

```json
{
  "version": 1,
  "id": "c30985da-7e3e-4d51-92e1-4566c3a01724",
  "name": "Circuit Sketch",
  "canvas_width": 1920.0,
  "canvas_height": 1080.0,
  "background_color": "#FFFFFF",
  "active_layer_id": "layer-uuid-1",
  "layers": [
    {
      "id": "layer-uuid-1",
      "name": "Background Grid",
      "visible": true,
      "locked": false,
      "opacity": 1.0,
      "elements": [
        {
          "id": "elem-uuid-1",
          "type": "rectangle",
          "x": 100.0,
          "y": 100.0,
          "width": 200.0,
          "height": 150.0,
          "rotation": 0.0,
          "stroke_color": "#000000",
          "stroke_width": 2.0,
          "stroke_style": "solid",
          "fill_color": "none"
        },
        {
          "id": "elem-uuid-2",
          "type": "freehand",
          "x": 0.0,
          "y": 0.0,
          "rotation": 0.0,
          "stroke_color": "#FF0000",
          "stroke_width": 3.0,
          "stroke_style": "solid",
          "fill_color": "none",
          "points": [[10.0, 10.0], [15.0, 12.0], [20.0, 25.0]]
        }
      ]
    }
  ]
}
```

### 3.2 Storage Registration (`pandaplot/storage/item_data_manager_factory.py`)

`SketchDataManager` implements `IItemDataManager`:
- `save(zip_file, sketch)` -> Writes `sketch_{id}.json` to `.pplot` zip.
- `load(zip_file, item_meta)` -> Reads `sketch_{id}.json` and instantiates `Sketch` model.

Register in storage factory:
```python
factory.register("sketch", Sketch, SketchDataManager(), "json")
```

---

## 4. Verification & Testing Plan

1. **Unit Tests (`tests/models/project/items/test_sketch.py`)**:
   - Verify creation of `Sketch`, default layer initialization, adding/removing layers.
   - Verify serialization `to_dict()` and `from_dict()` for all element types.
   - Verify integrity of element ordering in layers.
2. **Storage Persistence Unit Tests (`tests/storage/test_sketch_data_manager.py`)**:
   - Save `Sketch` into mock ZipFile / temp file.
   - Load back and verify deep equality of sketch properties, layers, and elements.
3. **Factory Registration Test**:
   - Ensure `ItemDataManagerFactory` resolves `"sketch"` correctly.
