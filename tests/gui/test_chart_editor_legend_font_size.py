"""Pure-matplotlib regression test for the legend font-size bug in
ChartEditor.update_chart (mirrors test_chart_editor_background_rendering.py):
Matplotlib silently ignores a `.legend(fontsize=...)` kwarg whenever `prop=`
is also passed, so the configured legend font size only takes effect if it's
merged into the `prop` dict alongside `family`."""
from matplotlib.figure import Figure


def render_legend_broken(fig, axes, handles, labels, font_size, font_family):
    """The pre-fix `.legend(...)` call: `fontsize=` and `prop={"family": ...}`
    passed together."""
    return axes.legend(handles, labels, fontsize=font_size, prop={"family": font_family})


def render_legend_fixed(fig, axes, handles, labels, font_size, font_family):
    """Mirrors the corrected `.legend(...)` call in ChartEditor.update_chart:
    the size is merged into `prop` instead of passed as a separate
    `fontsize=` kwarg."""
    return axes.legend(handles, labels, prop={"family": font_family, "size": font_size})


def _plot_one_series(fig):
    axes = fig.add_subplot(111)
    axes.plot([1, 2, 3], [1, 2, 3], label="Series 1")
    return axes, *axes.get_legend_handles_labels()


def test_broken_call_ignores_configured_font_size_when_prop_also_set():
    """Documents the bug: with both `fontsize=` and `prop=` (without `size`
    in `prop`), the legend text falls back to rcParams["legend.fontsize"],
    not the configured size."""
    fig = Figure()
    axes, handles, labels = _plot_one_series(fig)
    legend = render_legend_broken(fig, axes, handles, labels, 22, "DejaVu Sans")
    assert legend.get_texts()[0].get_fontsize() != 22


def test_fixed_call_applies_configured_font_size_with_font_family_set():
    fig = Figure()
    axes, handles, labels = _plot_one_series(fig)
    legend = render_legend_fixed(fig, axes, handles, labels, 22, "DejaVu Sans")
    assert legend.get_texts()[0].get_fontsize() == 22
    assert legend.get_texts()[0].get_fontfamily() == ["DejaVu Sans"]


def test_fixed_call_applies_default_font_size_of_ten():
    fig = Figure()
    axes, handles, labels = _plot_one_series(fig)
    legend = render_legend_fixed(fig, axes, handles, labels, 10, "DejaVu Sans")
    assert legend.get_texts()[0].get_fontsize() == 10
