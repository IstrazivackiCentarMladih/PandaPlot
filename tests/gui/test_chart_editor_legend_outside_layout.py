"""Regression test for the outside-legend clipping bug in
ChartEditor.update_chart.

A legend placed outside the axes via `bbox_to_anchor` (the Outside Right/
Top/Bottom/Custom positions -- see resolve_legend_placement) sits past the
axes' own bounding box, so `fig.tight_layout()` must run *after* the legend
exists for Matplotlib to shrink the axes and make room for it. Before the
fix, `tight_layout()` in `update_chart` only ran when a secondary axis was
present, so a single-axis chart with an outside/custom legend never got any
`tight_layout()` call at all -- the legend was clipped by the figure
boundary and never fully on-figure.

This exercises the real `apply_layout_with_legend` helper used by
`ChartEditorWidget.update_chart` (extracted so it can be tested without a
live QApplication/canvas)."""
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from pandaplot.gui.components.tabs.chart.chart_editor import apply_layout_with_legend


def _plot_and_place_legend_outside(fig):
    axes = fig.add_subplot(111)
    axes.plot([1, 2, 3], [1, 2, 3], label="Series One")
    handles, labels = axes.get_legend_handles_labels()
    legend = axes.legend(handles, labels, loc="center left", bbox_to_anchor=(1.02, 0.5))
    return axes, legend


def _legend_window_extent(fig, legend):
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    return legend.get_window_extent(renderer)


def test_outside_legend_is_clipped_without_any_tight_layout_call():
    """Documents the bug: on a single-axis chart the pre-fix code (gated on
    axes2 being present) never called tight_layout() at all, leaving the
    outside legend clipped by the figure edge."""
    fig = Figure(figsize=(6, 4))
    _axes, legend = _plot_and_place_legend_outside(fig)
    bbox = _legend_window_extent(fig, legend)
    assert bbox.x1 > fig.bbox.width


def test_apply_layout_with_legend_fits_outside_legend_on_single_axis_chart():
    """Mirrors the fixed `update_chart` sequence for a single-axis chart with
    an outside legend (no secondary axis, so the old axes2-gated call would
    never run): tight_layout() must still run so the legend lands fully
    on-figure."""
    fig = Figure(figsize=(6, 4))
    _axes, legend = _plot_and_place_legend_outside(fig)
    apply_layout_with_legend(fig, tight_layout_kwargs={}, legend_placed_outside=True)
    bbox = _legend_window_extent(fig, legend)
    assert bbox.x1 <= fig.bbox.width


def test_apply_layout_with_legend_runs_tight_layout_twice_when_legend_outside():
    """The extra pass is what accounts for the legend's own out-of-axes
    extent (unknown to Matplotlib on the first pass)."""
    fig = Figure(figsize=(6, 4))
    _plot_and_place_legend_outside(fig)
    calls = []
    fig.tight_layout = lambda **kwargs: calls.append(kwargs)
    apply_layout_with_legend(fig, tight_layout_kwargs={"pad": 2.0}, legend_placed_outside=True)
    assert calls == [{"pad": 2.0}, {"pad": 2.0}]


def test_apply_layout_with_legend_runs_tight_layout_once_when_legend_inside():
    fig = Figure(figsize=(6, 4))
    axes = fig.add_subplot(111)
    axes.plot([1, 2, 3], [1, 2, 3], label="Series One")
    axes.legend()
    calls = []
    fig.tight_layout = lambda **kwargs: calls.append(kwargs)
    apply_layout_with_legend(fig, tight_layout_kwargs={"pad": 2.0}, legend_placed_outside=False)
    assert calls == [{"pad": 2.0}]
