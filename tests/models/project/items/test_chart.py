"""Tests for the Chart model (pandaplot.models.project.items.chart.Chart)."""

import numpy as np

from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.fit_style import FitStyle
from pandaplot.models.chart.series_style import BarSeriesStyle, HistSeriesStyle, LineSeriesStyle, VectorSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import (
    Chart,
    DataSeries,
    FitData,
    restore_chart_state,
    snapshot_chart_state,
)


class TestFitDataStyle:
    """FitData.style is authoritative, auto-derived like DataSeries.style."""

    def test_style_auto_derives_to_a_default_fitstyle(self):
        fit = FitData(source_dataset_id="ds1", fit_type="linear",
                       x_data=np.array([1.0]), y_data=np.array([2.0]), label="Fit")

        assert isinstance(fit.style, FitStyle)
        assert fit.style.color == "#ff7f0e"
        assert fit.style.band_fill_enabled is True

    def test_style_is_respected_when_passed_explicitly(self):
        fit = FitData(source_dataset_id="ds1", fit_type="linear",
                       x_data=np.array([1.0]), y_data=np.array([2.0]), label="Fit",
                       style=FitStyle(color="#112233", band_fill_enabled=False))

        assert fit.style.color == "#112233"
        assert fit.style.band_fill_enabled is False

    def test_flat_style_fields_no_longer_exist(self):
        fit = FitData(source_dataset_id="ds1", fit_type="linear",
                       x_data=np.array([1.0]), y_data=np.array([2.0]), label="Fit")

        assert not hasattr(fit, "color")
        assert not hasattr(fit, "line_style")
        assert not hasattr(fit, "line_width")
        assert not hasattr(fit, "alpha")


class TestChartTypeIsChartTypeEnum:
    """Chart.chart_type is a ChartType(str, Enum), not a plain str -- but
    every existing string-literal comparison in the codebase keeps
    working, since ChartType subclasses str (same pattern as
    DataSeries.y_axis/YAxis)."""

    def test_constructor_coerces_string_to_charttype(self):
        chart = Chart(name="C", chart_type="scatter")

        assert chart.chart_type == ChartType.SCATTER
        assert isinstance(chart.chart_type, ChartType)

    def test_constructor_accepts_a_charttype_instance_directly(self):
        chart = Chart(name="C", chart_type=ChartType.VECTOR)

        assert chart.chart_type == ChartType.VECTOR

    def test_constructor_defaults_to_line(self):
        chart = Chart(name="C")

        assert chart.chart_type == ChartType.LINE

    def test_set_chart_type_coerces_string(self):
        chart = Chart(name="C", chart_type="line")

        chart.set_chart_type("bar")

        assert chart.chart_type == ChartType.BAR

    def test_string_equality_still_works(self):
        # Existing call sites throughout chart_editor.py/resolve_series_data
        # compare chart.chart_type directly to string literals -- this must
        # keep working unchanged.
        chart = Chart(name="C", chart_type="hist")

        assert chart.chart_type == "hist"
        assert chart.chart_type != "line"

    def test_to_dict_serializes_as_plain_string(self):
        chart = Chart(name="C", chart_type="vector")

        data = chart.to_dict()

        assert data["chart_type"] == "vector"
        assert isinstance(data["chart_type"], str)

    def test_from_dict_round_trips_chart_type(self):
        chart = Chart(name="C", chart_type="scatter")
        data = chart.to_dict()

        restored = Chart.from_dict(data)

        assert restored.chart_type == ChartType.SCATTER

    def test_from_dict_defaults_missing_chart_type_to_line(self):
        restored = Chart.from_dict({"name": "C"})

        assert restored.chart_type == ChartType.LINE


class TestDataSeriesTypeAndStyle:
    """series_type/style are new, optional, additive fields -- every
    existing DataSeries(...) construction site (none of which pass these
    two new kwargs) keeps working via their defaults."""

    def test_defaults_when_not_specified(self):
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y")

        assert series.series_type == SeriesType.LINE
        assert isinstance(series.style, LineSeriesStyle)

    def test_accepts_a_seriestype_instance(self):
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y", series_type=SeriesType.VECTOR)

        assert series.series_type == SeriesType.VECTOR

    def test_coerces_a_string_series_type(self):
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y", series_type="scatter")

        assert series.series_type == SeriesType.SCATTER

    def test_accepts_an_explicit_style_object(self):
        style = VectorSeriesStyle(vector_color="#ff0000")
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                             series_type=SeriesType.VECTOR, style=style)

        assert series.style is style
        assert series.style.vector_color == "#ff0000"


class TestChartSeriesTypeAndStyleRoundTrip:
    """A save-then-load cycle must reproduce series_type/style exactly --
    otherwise a migrated project's new fields would be silently dropped on
    the very next save."""

    def test_round_trips_series_type_and_style(self):
        chart = Chart(name="C", chart_type="line")
        style = LineSeriesStyle(color="#abcdef", line_width=3.5)
        chart.data_series.append(DataSeries(
            dataset_id="ds1", x_column="x", y_column="y",
            series_type=SeriesType.LINE, style=style,
        ))

        data = chart.to_dict()
        restored = Chart.from_dict(data)

        restored_series = restored.data_series[0]
        assert restored_series.series_type == SeriesType.LINE
        assert isinstance(restored_series.style, LineSeriesStyle)
        assert restored_series.style.color == "#abcdef"
        assert restored_series.style.line_width == 3.5

    def test_round_trips_a_series_constructed_with_no_explicit_style(self):
        # __post_init__ now auto-derives .style at construction time, so
        # this series already has a style before to_dict() ever runs --
        # round-tripping it must preserve that derived style, not lose it.
        chart = Chart(name="C", chart_type="line")
        chart.data_series.append(DataSeries(dataset_id="ds1", x_column="x", y_column="y"))

        data = chart.to_dict()
        restored = Chart.from_dict(data)

        assert isinstance(restored.data_series[0].style, LineSeriesStyle)

    def test_from_dict_defaults_series_type_to_chart_type_when_absent(self):
        # Simulates a legacy project not yet through
        # migrate_chart_legacy_to_v1 -- from_dict must still produce a
        # usable series_type.
        chart = Chart(name="C", chart_type="vector")
        raw = chart.to_dict()
        raw["data_series"] = [{
            "dataset_id": "ds1", "x_column": "x", "y_column": "y",
            # no "series_type" key at all.
        }]

        restored = Chart.from_dict(raw)

        assert restored.data_series[0].series_type == SeriesType.VECTOR


class TestSnapshotRestorePreservesStyleType:
    """snapshot_chart_state/restore_chart_state back the properties-panel
    cancel/undo flow. dataclasses.asdict(series) recursively flattens
    nested dataclasses to plain dicts -- DataSeries(**d) then constructs a
    DataSeries whose .style field holds that plain dict, not a
    reconstructed SeriesStyleBase instance, unless restore explicitly
    rebuilds it via style_cls."""

    def test_restore_reconstructs_style_as_a_dataclass_not_a_dict(self):
        chart = Chart(name="C", chart_type="line")
        style = LineSeriesStyle(color="#123456")
        chart.data_series.append(DataSeries(
            dataset_id="ds1", x_column="x", y_column="y",
            series_type=SeriesType.LINE, style=style,
        ))

        snapshot = snapshot_chart_state(chart)
        chart.data_series[0].style = LineSeriesStyle(color="#ffffff")  # simulate an in-progress edit
        restore_chart_state(chart, snapshot)

        restored_style = chart.data_series[0].style
        assert isinstance(restored_style, LineSeriesStyle)
        assert restored_style.color == "#123456"

    def test_restore_handles_a_series_constructed_with_no_explicit_style(self):
        # __post_init__ now auto-derives .style at construction time, so
        # this series already has a style before the snapshot is taken --
        # restore must preserve that derived style, not lose it.
        chart = Chart(name="C", chart_type="line")
        chart.data_series.append(DataSeries(dataset_id="ds1", x_column="x", y_column="y"))

        snapshot = snapshot_chart_state(chart)
        restore_chart_state(chart, snapshot)

        assert isinstance(chart.data_series[0].style, LineSeriesStyle)


class TestDataSeriesAutoDerivesStyle:
    """.style is auto-populated in __post_init__ whenever not explicitly
    given -- closing the gap Phase 3a's final review flagged (nothing
    populated .style for a series created after Phase 3a shipped).

    Since Phase 3c Task 4 deleted the flat styling fields (and the
    `derive_style` bridge that read them), a fresh series with no explicit
    `style=` now gets its style class's own defaults rather than anything
    derived from flat kwargs -- there are no flat kwargs left to derive
    from."""

    def test_fresh_line_series_gets_default_line_style(self):
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                             series_type=SeriesType.LINE)

        assert isinstance(series.style, LineSeriesStyle)
        assert series.style == LineSeriesStyle()

    def test_fresh_vector_series_gets_default_vector_style(self):
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                             series_type=SeriesType.VECTOR)

        assert isinstance(series.style, VectorSeriesStyle)
        assert series.style == VectorSeriesStyle()

    def test_explicit_style_is_not_overwritten(self):
        explicit = LineSeriesStyle(color="#explicit")
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                             series_type=SeriesType.LINE, style=explicit)

        assert series.style is explicit


class TestSetChartTypeRetypesSeries:
    """set_chart_type must retype only series whose current type is NOT
    allowed under the new chart type -- otherwise chart_editor.py's
    renderer picks its dispatch function from the chart's new type but
    still finds series whose .style is the OLD style class, and crashes
    trying to read fields the wrong class doesn't declare (the
    derive_style-removal regression fixed in Phase 3c). Series whose type
    IS allowed under the new chart type (e.g. a LINE series when the
    chart becomes "vector", since Vector's spec allows {VECTOR, LINE})
    must be left completely untouched, since mixed series types are
    legitimate under that combination."""

    def test_disallowed_series_type_gets_retyped_to_the_new_chart_defaults(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#112233"))

        chart.set_chart_type("hist")

        series = chart.data_series[0]
        assert series.series_type == SeriesType.HIST
        assert isinstance(series.style, HistSeriesStyle)
        assert series.style.color == "#112233"

    def test_vector_to_line_carries_vector_color_into_color(self):
        chart = Chart(name="C", chart_type="vector")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=VectorSeriesStyle(vector_color="#445566"))

        chart.set_chart_type("line")

        series = chart.data_series[0]
        assert series.series_type == SeriesType.LINE
        assert isinstance(series.style, LineSeriesStyle)
        assert series.style.color == "#445566"

    def test_line_series_stays_line_when_chart_becomes_vector_since_line_is_allowed(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#112233"))
        original_style = chart.data_series[0].style

        chart.set_chart_type("vector")

        series = chart.data_series[0]
        assert series.series_type == SeriesType.LINE
        assert series.style is original_style

    def test_scatter_series_stays_scatter_across_line_and_bar_since_both_allow_it(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               series_type=SeriesType.SCATTER)
        original_style = chart.data_series[0].style

        chart.set_chart_type("bar")

        series = chart.data_series[0]
        assert series.series_type == SeriesType.SCATTER
        assert series.style is original_style

    def test_setting_the_same_type_is_a_no_op(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#112233"))
        original_style = chart.data_series[0].style

        chart.set_chart_type("line")

        assert chart.data_series[0].style is original_style

    def test_multi_series_chart_each_keeps_its_own_color(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#111111"))
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#222222"))

        chart.set_chart_type("bar")

        assert chart.data_series[0].series_type == SeriesType.BAR
        assert isinstance(chart.data_series[0].style, BarSeriesStyle)
        assert chart.data_series[0].style.color == "#111111"
        assert chart.data_series[1].series_type == SeriesType.BAR
        assert isinstance(chart.data_series[1].style, BarSeriesStyle)
        assert chart.data_series[1].style.color == "#222222"

    def test_mixed_chart_only_retypes_the_disallowed_series(self):
        """A chart with one LINE and one HIST series switching to "vector"
        (allowed_series_types = {VECTOR, LINE}): the LINE series stays
        untouched, the HIST series (not allowed) gets retyped to VECTOR."""
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#111111"))
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               series_type=SeriesType.HIST,
                               style=HistSeriesStyle(color="#222222"))
        line_style = chart.data_series[0].style

        chart.set_chart_type("vector")

        assert chart.data_series[0].series_type == SeriesType.LINE
        assert chart.data_series[0].style is line_style

        retyped = chart.data_series[1]
        assert retyped.series_type == SeriesType.VECTOR
        assert isinstance(retyped.style, VectorSeriesStyle)
        assert retyped.style.vector_color == "#222222"


class TestRetypeSeries:
    """Chart.retype_series retypes a single series explicitly -- the same
    per-series logic set_chart_type applies in bulk when a chart-type
    change makes a series' type disallowed, but callable directly for an
    explicit per-series type change (Phase 4c's Series Type selector)."""

    def test_retypes_a_single_series_and_carries_color(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#112233"))

        chart.retype_series(0, "hist")

        series = chart.data_series[0]
        assert series.series_type == SeriesType.HIST
        assert isinstance(series.style, HistSeriesStyle)
        assert series.style.color == "#112233"

    def test_retyping_to_vector_carries_color_into_vector_color(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#445566"))

        chart.retype_series(0, "vector")

        series = chart.data_series[0]
        assert series.series_type == SeriesType.VECTOR
        assert isinstance(series.style, VectorSeriesStyle)
        assert series.style.vector_color == "#445566"

    def test_retyping_to_the_same_type_is_a_no_op(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#112233"))
        original_style = chart.data_series[0].style

        chart.retype_series(0, "line")

        assert chart.data_series[0].style is original_style

    def test_only_the_targeted_series_is_retyped(self):
        chart = Chart(name="C", chart_type="line")
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#111111"))
        chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                               style=LineSeriesStyle(color="#222222"))
        untouched_style = chart.data_series[1].style

        chart.retype_series(0, "scatter")

        assert chart.data_series[0].series_type == SeriesType.SCATTER
        assert chart.data_series[1].series_type == SeriesType.LINE
        assert chart.data_series[1].style is untouched_style


class TestChartAddDataSeriesDefaultsSeriesType:
    """add_data_series defaults series_type from the chart's own type when
    the caller doesn't pass one -- without this, every series added via
    the Data tab or the wizard would default to SeriesType.LINE regardless
    of the chart's real type (the exact gap Phase 3a's review flagged)."""

    def test_defaults_series_type_from_chart_type(self):
        chart = Chart(name="C", chart_type="bar")

        series = chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y")

        assert series.series_type == SeriesType.BAR
        assert isinstance(series.style, BarSeriesStyle)

    def test_explicit_series_type_kwarg_is_respected(self):
        chart = Chart(name="C", chart_type="line")

        series = chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                                        series_type=SeriesType.SCATTER)

        assert series.series_type == SeriesType.SCATTER

    def test_vector_chart_add_series_gets_vector_style_with_passed_color(self):
        chart = Chart(name="C", chart_type="vector")

        series = chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y",
                                        style=VectorSeriesStyle(vector_color="#abcdef"))

        assert series.series_type == SeriesType.VECTOR
        assert isinstance(series.style, VectorSeriesStyle)
        assert series.style.vector_color == "#abcdef"
