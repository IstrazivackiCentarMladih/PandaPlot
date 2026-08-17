"""Tests for DataSeries vector-plot fields and their round-trip through Chart."""
from pandaplot.models.chart.series_style import VectorSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import Chart, DataSeries, assign_series_column_ids


def test_data_series_vector_column_fields_have_defaults():
    series = DataSeries(dataset_id="ds1")
    assert series.u_column_id == ""
    assert series.v_column_id == ""
    assert series.magnitude_column_id == ""


def test_vector_series_style_has_defaults():
    series = DataSeries(dataset_id="ds1", series_type=SeriesType.VECTOR)
    assert series.style.vector_color == "#1f77b4"
    assert series.style.vector_colormap == ""
    assert series.style.vector_scale == 0.0
    assert series.style.vector_width == 0.005
    assert series.style.vector_head_width == 3.0
    assert series.style.vector_head_length == 5.0
    assert series.style.vector_head_axis_length == 4.5


def test_chart_to_dict_from_dict_round_trips_vector_fields():
    chart = Chart(name="Vec Chart", chart_type="vector")
    chart.add_data_series(
        "ds1", x_column_id="x", y_column_id="y",
        u_column_id="u", v_column_id="v", magnitude_column_id="m",
        style=VectorSeriesStyle(
            vector_color="#ff0000", vector_colormap="plasma",
            vector_scale=2.5, vector_width=0.01,
            vector_head_width=4.0, vector_head_length=6.0, vector_head_axis_length=5.5,
        ),
        label="Field",
    )

    data = chart.to_dict()
    restored = Chart.from_dict(data)

    series = restored.data_series[0]
    assert series.u_column_id == "u"
    assert series.v_column_id == "v"
    assert series.magnitude_column_id == "m"
    assert series.style.vector_color == "#ff0000"
    assert series.style.vector_colormap == "plasma"
    assert series.style.vector_scale == 2.5
    assert series.style.vector_width == 0.01
    assert series.style.vector_head_width == 4.0
    assert series.style.vector_head_length == 6.0
    assert series.style.vector_head_axis_length == 5.5


def test_chart_from_dict_defaults_vector_fields_for_legacy_charts():
    """A chart saved before this feature (or before Phase 3c's typed
    `style` object) existed has no vector keys, or even no `style` key,
    at all."""
    chart = Chart(name="Legacy", chart_type="line")
    chart.add_data_series("ds1", x_column_id="x", y_column_id="y")
    data = chart.to_dict()
    for key in ("u_column_id", "v_column_id", "magnitude_column_id", "style"):
        del data["data_series"][0][key]

    restored = Chart.from_dict(data)
    series = restored.data_series[0]
    assert series.u_column_id == ""
    assert series.style.color == "#1f77b4"


def test_assign_series_column_ids_fills_u_and_v():
    class _FakeDataset:
        def column_id(self, name):
            return {"u_name": "u-id", "v_name": "v-id"}.get(name)

    series = DataSeries(dataset_id="ds1", u_column="u_name", v_column="v_name")
    assign_series_column_ids(series, _FakeDataset())
    assert series.u_column_id == "u-id"
    assert series.v_column_id == "v-id"


def test_assign_series_column_ids_fills_magnitude():
    class _FakeDataset:
        def column_id(self, name):
            return {"mag_name": "mag-id"}.get(name)

    series = DataSeries(dataset_id="ds1", magnitude_column="mag_name")
    assign_series_column_ids(series, _FakeDataset())
    assert series.magnitude_column_id == "mag-id"
