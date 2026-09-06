# Sub-Issue 4 Design Specification: Measurement Probes & DC/AC Simulation (Stretch)

**Parent Issue:** [#149 - Add electronics circuit sketching support](https://github.com/Youth-Research-Center/PandaPlot/issues/149)
**Depends on:** Sub-Issues 1-3 (components, wires, transforms)
**Milestone:** 11. Circuit Sketching
**Labels:** `area: chart-types`, `effort: l`, `enhancement`, `priority: low`

---

## 1. Scope and risk note — read before estimating

This is a materially different kind of work from Sub-Issues 1-3: those are drawing-tool features that extend an established pattern (a new `SketchElement` + `QGraphicsItem` + `Command`, same shape as five). This sub-issue is a **numeric solver** (nodal analysis) with no precedent anywhere in PandaPlot's codebase, plus a UI for entering simulation parameters and routing results into a `Dataset`/`Chart`. It's also the one place the original proposal (PR #356) most overreached — it specified a general Modified-Nodal-Analysis engine with AC frequency sweep and transient analysis as if it were routine, undoable-command-shaped work like the rest.

**Recommendation: spike before committing to a full design.** Build a throwaway DC-only solver for a single fixed topology (e.g. one voltage source + up to 3 resistors in series/parallel) against 1-2 hand-computed test circuits, and confirm the node/wire model from Sub-Issue 2 (`start_ref`/`end_ref` scanning) is actually enough to build a solvable node list from — or whether it needs the `CircuitGraph` structure Sub-Issue 2 deliberately deferred. Only after that spike should AC/transient analysis, probe placement UI, and Chart integration be scoped in detail; specifying all of that now would repeat the same premature-design mistake being corrected elsewhere in this milestone.

The rest of this document describes the target shape once the spike de-risks it — treat it as a direction, not a committed design.

---

## 2. Target Shape (post-spike)

### 2.1 Measurement elements
- `VoltmeterElement(SketchElement)` — placed across two terminals (like a 1-terminal-pair component in Sub-Issue 1's model), reads the DC voltage difference at the connected nodes once a simulation has run.
- `AmmeterElement(SketchElement)` — placed in series along a wire (splits the wire into two, both ends referencing the ammeter's two terminals), reads branch current.

### 2.2 Simulation
```
pandaplot/analysis/circuit_simulator.py   # only if analysis code doesn't already have a home under pandaplot/analysis/ for chart-side numeric work — confirm against the existing analysis modules before adding a new top-level package
```
- Build the node list by scanning `WireElement.start_ref`/`end_ref` across the active layer (or the `CircuitGraph` from Sub-Issue 2, if the spike shows the flat scan doesn't scale).
- DC solve via `numpy.linalg.solve` on a small dense MNA matrix — `scipy.sparse` is unnecessary at the circuit sizes a sketch tool will realistically contain (tens of components, not thousands); don't add a `scipy` dependency for this unless the spike shows an actual need.
- AC/transient analysis is out of scope until DC is solid and there's user demand — do not build it in the same pass as the DC spike.

### 2.3 Results
- "Run Simulation" toolbar action, gated to only appear when the active `Sketch` contains circuit elements.
- Results populate a new `Dataset` item (reusing the existing `Dataset`/`Chart` pipeline exactly as-is — no new visualization code), rather than a bespoke in-canvas readout system, so a user can chart V(t)/I(t) with tools they already know.

---

## 3. Verification & Testing Plan (spike phase)

1. Hand-solve 2 simple DC circuits (a series resistor divider, a parallel resistor pair) and assert the simulator's node voltages match within a small numeric tolerance.
2. Confirm the wire/terminal model from Sub-Issue 2 is sufficient to build the node list without modification, or document exactly what it's missing.

Full test plan for probes, AC/transient, and Chart/Dataset integration should be written once the spike's findings are in — specifying it now would be guessing.
