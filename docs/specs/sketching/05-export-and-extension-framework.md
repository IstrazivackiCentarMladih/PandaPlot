# Sub-Issue 5 Design Specification: Image Export and Domain Extension Framework Foundation

**Parent Issue:** [#148 - Add a sketching tab (freehand/shape drawing canvas item)](https://github.com/Youth-Research-Center/PandaPlot/issues/148)
**Milestone:** Backlog
**Labels:** `area: chart-types`, `effort: s`, `enhancement`, `priority: medium`

---

## 1. Goal & Objectives

Provide export options for sketches to standard image/vector formats (PNG, SVG, PDF, JPEG) with customizable export options, and establish an abstract Extension Framework foundation so downstream domain-specific drawing features (such as electronics circuit components like resistors, capacitors, logic gates) can seamlessly extend the sketch canvas.

---

## 2. Sketch Image Export

```
pandaplot/gui/dialogs/sketch/
└── export_sketch_dialog.py     # Dialog for format, resolution & background settings
```

### 2.1 Export Features & Options
- **Formats**: PNG (raster with alpha channel), JPEG (compressed raster), SVG (vector graphic), PDF (document vector).
- **Export Region Options**:
  - `Entire Canvas Bounds`: Full `canvas_width` x `canvas_height`.
  - `Bounding Box of Elements`: Tight cropping around drawn elements with configurable padding (default: 10px).
- **Background Options**:
  - `Solid Color` (default canvas background).
  - `Transparent` (for PNG / SVG).
- **Resolution / Scale**: Scale factor (`1x`, `2x`, `4x`, custom DPI: 72, 150, 300, 600 DPI for high-resolution publication export).
- **Layer Selection**: Export all visible layers vs export specific layers.

### 2.2 Implementation Detail
Using `QGraphicsScene.render()` onto `QPainter` target:
- For PNG/JPEG: Render onto `QImage` / `QPixmap` with desired DPI resolution.
- For SVG: Render onto `QSvgGenerator`.
- For PDF: Render onto `QPdfWriter` / `QPrinter`.

---

## 3. Extension Framework Foundation for Domain Features

The issue description explicitly specifies:
> "This is intended as the foundation other structured-drawing features can build on — see the electronics circuit sketching follow-up issue, which extends this with domain-specific components (resistors, capacitors, etc.)."

### 3.1 Domain Extension Architecture (`pandaplot/gui/components/tabs/sketch/extensions/`)

```python
# Base Extension Class
class SketchExtension(ABC):
    @property
    @abstractmethod
    def extension_id(self) -> str:
        """Unique extension identifier e.g. 'electronics_circuit'."""
        pass

    @abstractmethod
    def get_custom_tools(self) -> list[BaseTool]:
        """Return custom drawing tools to add to sketch toolbar."""
        pass

    @abstractmethod
    def get_custom_element_factories(self) -> dict[str, type[SketchElement]]:
        """Return custom element classes for deserialization."""
        pass
```

### 3.2 `SketchComponentRegistry`
Global registry singleton where external plugins or domain modules register custom element types and tool items:
```python
class SketchComponentRegistry:
    def register_extension(self, extension: SketchExtension) -> None:
        ...
```

This guarantees that future features (like electronics components) can plug in without modifying core sketch code.

---

## 4. Verification & Testing Plan

1. **Export Tests (`tests/gui/sketch/test_export_sketch.py`)**:
   - Verify rendering `SketchCanvas` to temporary PNG, SVG, PDF, JPEG files.
   - Test transparent background export options.
   - Verify DPI scaling factors produce correct image dimensions.
2. **Extension Framework Tests (`tests/gui/sketch/test_sketch_extension.py`)**:
   - Register a dummy custom `SketchExtension` with custom tool and shape element.
   - Confirm tool appears in toolbar and element serializes/deserializes correctly.
