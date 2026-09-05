# Electronics Circuit Sketching Support (Issue #149 Subissues & Design Specifications)

This document breaks down issue **#149 (Add electronics circuit sketching support)** into 6 modular subissues, all assigned to the **Backlog** milestone. Each subissue includes a description, metadata, dependencies, and a technical design specification tailored for PandaPlot's PySide6 architecture.

---

## Issue Overview & Roadmap

Issue #149 extends PandaPlot's Sketching Tab (#148) with domain-specific tools for drawing, editing, persisting, and simulating simple electrical and electronics circuit diagrams.

```
Subissue Breakdown:
1. #149-1: Electronics Circuit Component Palette & Symbols (Resistor, Capacitor, Diode, Inductor, Voltage Sources, Ground)
2. #149-2: Wire Connection Routing and Terminal Snapping
3. #149-3: Component Property Labeling and Value Annotations
4. #149-4: Circuit Component Transformation (Rotation and Flipping)
5. #149-5: Circuit Diagram Persistence and Image/SVG Export
6. #149-6: Basic Circuit Measurement Devices & DC/AC Simulation
```

---

## Subissue 1: Electronics Circuit Component Palette & Symbols

### Metadata
- **Title**: Circuit Sketching: Component Palette & Standard Symbols
- **Milestone**: `Backlog`
- **Labels**: `area: chart-types`, `enhancement`, `priority: medium`, `effort: m`
- **Depends On**: `#148` (Sketching Tab foundation)

### Description
Introduce a domain-specific component palette tool pane within the Sketching Tab containing standard schematic symbols for passive and active electronic components:
- Resistor (ANSI zig-zag and IEC box)
- Capacitor (polarized and non-polarized)
- Diode (standard PN junction diode, LED)
- Coil / Inductor
- DC & AC Voltage Sources, Current Source
- Ground (GND) / Earth symbol

### Design Specification
1. **Model Layer (`pandaplot/models/sketch/components/`)**:
   - Define `CircuitComponentType` enum: `RESISTOR`, `CAPACITOR`, `CAPACITOR_POLARIZED`, `DIODE`, `LED`, `INDUCTOR`, `VOLTAGE_DC`, `VOLTAGE_AC`, `CURRENT_DC`, `GROUND`.
   - Extend base `SketchElement` with `CircuitComponentElement`:
     - Properties: `component_type: CircuitComponentType`, `terminals: List[TerminalPoint]`, `parameters: Dict[str, Any]`.
     - `TerminalPoint`: `id: str`, `relative_x: float`, `relative_y: float`, `direction: Vector2D`.
2. **GUI Layer (`pandaplot/gui/components/sketch/`)**:
   - `CircuitPalettePanel`: A QToolPalette / QListView sidebar widget displaying component icons.
   - `QGraphicsCircuitItem`: Custom `QGraphicsItemGroup` or `QGraphicsPathItem` subclass for rendering vector symbols using `QPainterPath`.
   - Drawing standard vector graphics paths adhering to IEEE 315 / IEC 60617 schematic standards.
3. **Commands (`pandaplot/commands/sketch/`)**:
   - `AddCircuitComponentCommand`: Adds `CircuitComponentElement` to `SketchModel`. Supports undo/redo.
4. **Events**:
   - Emit `SketchEvents.ELEMENT_ADDED` when dropped onto canvas.

---

## Subissue 2: Wire Connection Routing and Terminal Snapping

### Metadata
- **Title**: Circuit Sketching: Wire Routing, Connection Points, and Grid/Terminal Snapping
- **Milestone**: `Backlog`
- **Labels**: `area: chart-types`, `enhancement`, `priority: high`, `effort: l`
- **Depends On**: Subissue 1 (#149-1)

### Description
Implement intelligent wire creation, terminal snapping, and automatic line routing so components remain connected when moved around the sketch canvas.

### Design Specification
1. **Model Layer (`pandaplot/models/sketch/wire.py`)**:
   - `WireElement`: Represents a conductive connection.
     - `start_terminal: Optional[TerminalRef]`, `end_terminal: Optional[TerminalRef]`.
     - `waypoints: List[Point2D]`: Intermediate orthogonal bend points (x, y).
   - `CircuitGraph`: Topological representation connecting `CircuitComponentElement` nodes and `WireElement` edges.
2. **Snapping & Routing Engine (`pandaplot/services/sketch/`)**:
   - `TerminalSnappingService`: Calculates magnetic snap distance (e.g. 10px radius) between wire endpoints and component terminal points.
   - `OrthogonalWireRouter`: Manhattan routing algorithm (A* pathfinding or minimum-bend heuristic) to auto-route wires around obstacles or along grid lines.
3. **GUI Layer**:
   - `QGraphicsWireItem`: Renders polyline with connection dot indicators at junctions (T-junctions / 4-way dots).
   - Dynamic terminal highlight anchors rendered when drawing wires near component pins.
4. **Commands**:
   - `ConnectWireCommand`, `DisconnectWireCommand`, `MoveComponentWithWiresCommand` (re-calculates attached wire geometry on component translate).

---

## Subissue 3: Component Property Labeling and Value Annotations

### Metadata
- **Title**: Circuit Sketching: Component Property Labeling and Value Annotations
- **Milestone**: `Backlog`
- **Labels**: `area: chart-types`, `enhancement`, `priority: medium`, `effort: m`
- **Depends On**: Subissue 1 (#149-1)

### Description
Allow users to attach, edit, and position schematic labels and physical values (e.g., R1 = 10 kΩ, C2 = 100 µF, Vin = 5 V) for components in the circuit sketch.

### Design Specification
1. **Model Layer**:
   - `ComponentAnnotation`: Sub-object on `CircuitComponentElement`.
     - `designator: str` (e.g., `R1`, `C1`, `D1`).
     - `value: str` or `value_num: float`, `unit: str` (e.g., `10k`, `Ohm`).
     - `visible: bool`, `relative_offset: Point2D`, `font_options: FontConfig`.
2. **GUI Layer**:
   - In-place double-click text editing using `QGraphicsTextItem` anchored to the parent `QGraphicsCircuitItem`.
   - `ComponentPropertyDialog` / Properties Inspector panel for setting values, designators, and metric prefixes (p, n, µ, m, k, M, G).
3. **LaTeX / Matplotlib MathText Support**:
   - Option to render complex subscripts and SI units using LaTeX formatting (consistent with PandaPlot's note and chart math rendering).
4. **Commands**:
   - `UpdateComponentPropertiesCommand`: Updates designator/value and supports undo/redo.

---

## Subissue 4: Circuit Component Transformation (Rotation and Flipping)

### Metadata
- **Title**: Circuit Sketching: Component Rotation and Flipping Transformations
- **Milestone**: `Backlog`
- **Labels**: `area: chart-types`, `enhancement`, `priority: medium`, `effort: s`
- **Depends On**: Subissue 1 (#149-1), Subissue 2 (#149-2)

### Description
Provide tools and shortcuts to rotate components in 90-degree increments and flip them horizontally or vertically, while preserving attached wire connections and maintaining upright text labels.

### Design Specification
1. **Model Layer**:
   - `CircuitComponentElement.rotation: int` (0, 90, 180, 270 degrees).
   - `CircuitComponentElement.flip_horizontal: bool`, `CircuitComponentElement.flip_vertical: bool`.
   - Transform matrix calculation mapping terminal local coordinates to scene coordinates: T_scene = T_pos * R(theta) * S(s_x, s_y) * T_local.
2. **GUI & UX Layer**:
   - Context menu items & hotkeys: `R` (Rotate 90° clockwise), `Shift+R` (Rotate counter-clockwise), `H` (Flip horizontal), `V` (Flip vertical).
   - Rotation handles on bounding box selection in `QGraphicsScene`.
   - Text orientation lock: Keeps designator and value labels upright regardless of component rotation angle.
3. **Wire Updating**:
   - Trigger `OrthogonalWireRouter` update on connected wires whenever component transforms change.
4. **Commands**:
   - `TransformComponentCommand(component_id, new_rotation, new_flip)`: Undoable operation.

---

## Subissue 5: Circuit Diagram Persistence and Image/SVG Export

### Metadata
- **Title**: Circuit Sketching: Project File Persistence and High-Resolution Image/SVG Export
- **Milestone**: `Backlog`
- **Labels**: `area: chart-types`, `enhancement`, `priority: medium`, `effort: m`
- **Depends On**: Subissue 1 (#149-1), Subissue 2 (#149-2), Subissue 3 (#149-3)

### Description
Serialize circuit components, wires, labels, and topology into PandaPlot project files (`.pplot`) and support exporting circuit diagrams to PNG, JPG, PDF, and SVG vector formats.

### Design Specification
1. **Storage Layer (`pandaplot/storage/sketch_data_manager.py`)**:
   - Serialize `SketchItem` containing circuit elements into `sketch_{id}.json` inside the `.pplot` ZIP container.
   - JSON Schema for circuit elements:
     ```json
     {
       "id": "comp_12",
       "type": "circuit_component",
       "component_type": "RESISTOR",
       "position": [100.0, 250.0],
       "rotation": 90,
       "designator": "R1",
       "value": "1k",
       "terminals": [{"id": "t1", "x": -20, "y": 0}, {"id": "t2", "x": 20, "y": 0}]
     }
     ```
2. **Export Engine**:
   - `ExportCircuitImageCommand`:
     - Raster export (PNG/JPEG) via `QRender` or `QPainter` onto high-DPI `QImage`.
     - Vector export (SVG) via `QSvgGenerator` for crisp inclusion in publications.
     - PDF export via `QPrinter` / `QPdfWriter`.
3. **Compatibility**:
   - Migration logic registered in `pandaplot/models/migrations/` for schema upgrades.

---

## Subissue 6: Basic Circuit Measurement Devices & DC/AC Simulation

### Metadata
- **Title**: Circuit Sketching: Measurement Instruments and Simple DC/AC Circuit Simulation
- **Milestone**: `Backlog`
- **Labels**: `area: chart-types`, `enhancement`, `priority: low`, `effort: l`
- **Depends On**: Subissue 1 (#149-1), Subissue 2 (#149-2), Subissue 3 (#149-3)

### Description
Add virtual measuring instruments (Voltmeter, Ammeter, Oscilloscope probe) and a background DC/AC nodal analysis simulation engine (using SciPy/NumPy) to solve voltages and currents and plot waveforms in PandaPlot charts.

### Design Specification
1. **Measurement Devices**:
   - `VoltmeterElement` (placed in parallel across two nodes).
   - `AmmeterElement` (placed in series along a wire).
   - `OscilloscopeProbeElement` (samples transient voltage over time).
2. **Simulation Engine (`pandaplot/analysis/circuit_simulator.py`)**:
   - `NodalAnalysisEngine`:
     - Constructs Modified Nodal Analysis (MNA) system matrices A * x = z using `scipy.sparse` / `numpy.linalg`.
     - Solves for node voltages V_n and branch currents I_b for DC circuits.
     - Performs AC frequency sweep / transient analysis for RLC circuits.
3. **Integration with PandaPlot Charts & Datasets**:
   - "Run Simulation" toolbar action in Sketching Tab.
   - Simulation results automatically populate a new `Dataset` item in the project tree.
   - Probes can directly generate a live `Chart` item showing transient response V(t) or I(t) or frequency response (Bode plot).
4. **GUI Layer**:
   - Interactive readout overlays on Voltmeters/Ammeters on the sketch canvas.
   - Simulation parameter dialog (DC sweep parameters, AC frequency range, transient time step dt).
