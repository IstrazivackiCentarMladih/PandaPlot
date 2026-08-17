"""Tests for the Chart model (pandaplot.models.project.items.chart.Chart)."""

from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_style import BarSeriesStyle, LineSeriesStyle, VectorSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import Chart, DataSeries, restore_chart_state, snapshot_chart_state


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
        # Simulates a v1 project not yet through migrate_chart_v1_to_v2
        # (Task 5) -- from_dict must still produce a usable series_type.
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
    populated .style for a series created after Phase 3a shipped)."""

    def test_fresh_line_series_gets_a_derived_style(self):
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                             series_type=SeriesType.LINE, color="#112233")

        assert isinstance(series.style, LineSeriesStyle)
        assert series.style.color == "#112233"

    def test_fresh_vector_series_gets_a_derived_vector_style(self):
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                             series_type=SeriesType.VECTOR, vector_color="#00ff00")

        assert isinstance(series.style, VectorSeriesStyle)
        assert series.style.vector_color == "#00ff00"

    def test_explicit_style_is_not_overwritten(self):
        explicit = LineSeriesStyle(color="#explicit")
        series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                             series_type=SeriesType.LINE, color="#derived-would-be-this",
                             style=explicit)

        assert series.style is explicit


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
                                        vector_color="#abcdef")

        assert series.series_type == SeriesType.VECTOR
        assert isinstance(series.style, VectorSeriesStyle)
        assert series.style.vector_color == "#abcdef"
