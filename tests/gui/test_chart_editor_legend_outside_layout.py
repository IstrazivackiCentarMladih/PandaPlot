"""Pure-matplotlib regression test for the outside-legend clipping bug in
ChartEditor.update_chart (mirrors test_chart_editor_background_rendering.py
and test_chart_editor_legend_font_size.py).

A legend placed outside the axes via `bbox_to_anchor` (the Outside Right/
Top/Bottom/Custom positions -- see resolve_legend_placement) sits past the
axes' own bounding box, so `fig.tight_layout()` must run *after* the legend
exists for Matplotlib to shrink the axes and make room for it. Before the
fix, `tight_layout()` in `update_chart` only ran when a secondary axis was
present, so a single-axis chart with an outside/custom legend never got any
`tight_layout()` call at all -- the legend was clipped by the figure
boundary and never fully on-figure.
"""
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


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


def test_outside_legend_is_clipped_without_tight_layout_after_legend():
    """Documents the bug: no tight_layout() call at all (the single-axis
    case pre-fix) leaves the outside legend clipped by the figure edge."""
    fig = Figure(figsize=(6, 4))
    _axes, legend = _plot_and_place_legend_outside(fig)
    bbox = _legend_window_extent(fig, legend)
    assert bbox.x1 > fig.bbox.width


def test_outside_legend_fits_when_tight_layout_runs_after_legend_added():
    """Mirrors the fixed `update_chart` sequence: tight_layout() is called
    (again, if needed) after the legend is added, so Matplotlib shrinks the
    axes to make room for it and the legend lands fully on-figure."""
    fig = Figure(figsize=(6, 4))
    _axes, legend = _plot_and_place_legend_outside(fig)
    fig.tight_layout()
    bbox = _legend_window_extent(fig, legend)
    assert bbox.x1 <= fig.bbox.width
