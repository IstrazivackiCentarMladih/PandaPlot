"""Serialization + defaults for the colormap/heatmap chart fields on DataSeries."""
from pandaplot.models.chart.chart_configuration import ChartType
from pandaplot.models.project.items.chart import Chart, DataSeries


def test_data_series_color_mapping_defaults():
    series = DataSeries(dataset_id="ds1")
    assert series.z_column_id == ""
    assert series.z_column == ""
    assert series.colormap == "viridis"
    assert series.colorbar_show is True
    assert series.colorbar_label == ""
    assert series.color_scale_auto is True


def test_chart_type_enum_has_colormap_and_heatmap():
    assert ChartType.COLORMAP.value == "colormap"
    assert ChartType.HEATMAP.value == "heatmap"


def test_chart_round_trips_color_mapping_fields():
    chart = Chart(name="Heat", chart_type="heatmap")
    chart.add_data_series(
        dataset_id="ds1", x_column_id="xid", y_column_id="yid", z_column_id="zid",
        colormap="plasma", colorbar_show=False, colorbar_label="Temp",
        color_scale_auto=False, color_vmin=-2.5, color_vmax=7.5,
    )

    data = chart.to_dict()
    series_dict = data["data_series"][0]
    assert data["chart_type"] == "heatmap"
    assert series_dict["z_column_id"] == "zid"
    assert series_dict["colormap"] == "plasma"
    assert series_dict["colorbar_show"] is False
    assert series_dict["colorbar_label"] == "Temp"
    assert series_dict["color_scale_auto"] is False
    assert series_dict["color_vmin"] == -2.5
    assert series_dict["color_vmax"] == 7.5

    restored = Chart.from_dict(data)
    rs = restored.data_series[0]
    assert restored.chart_type == "heatmap"
    assert rs.z_column_id == "zid"
    assert rs.colormap == "plasma"
    assert rs.colorbar_show is False
    assert rs.colorbar_label == "Temp"
    assert rs.color_scale_auto is False
    assert rs.color_vmin == -2.5
    assert rs.color_vmax == 7.5


def test_legacy_chart_without_color_fields_gets_defaults():
    # A chart saved before the color-mapping fields existed must still load,
    # falling back to the defaults (merged over by from_dict's .get()s).
    chart = Chart(name="Old", chart_type="line")
    chart.add_data_series(dataset_id="ds1", x_column_id="xid", y_column_id="yid")
    data = chart.to_dict()
    for key in ("z_column_id", "colormap", "colorbar_show", "color_scale_auto",
                "color_vmin", "color_vmax"):
        data["data_series"][0].pop(key, None)

    restored = Chart.from_dict(data)
    rs = restored.data_series[0]
    assert rs.z_column_id == ""
    assert rs.colormap == "viridis"
    assert rs.colorbar_show is True
    assert rs.color_scale_auto is True
