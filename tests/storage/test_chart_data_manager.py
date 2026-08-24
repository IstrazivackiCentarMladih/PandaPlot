"""Tests for ChartDataManager's load path running the per-item chart
migration dispatcher before constructing the Chart."""
import io
from unittest.mock import patch
from zipfile import ZipFile

from pandaplot.models.project.items.chart import Chart
from pandaplot.storage.chart_data_manager import ChartDataManager


def _round_trip(chart: Chart, schema_version: int = 1) -> Chart:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zf:
        ChartDataManager().save(chart, zf, "items/test-chart")

    buffer.seek(0)
    with ZipFile(buffer, "r") as zf:
        return ChartDataManager().load(Chart, zf, "items/test-chart", schema_version)


def test_round_trip_preserves_chart_type():
    chart = Chart(id="chart-1", name="My Chart", chart_type="scatter")

    loaded = _round_trip(chart)

    assert loaded.chart_type == "scatter"


def test_load_runs_migrate_chart_before_constructing():
    chart = Chart(id="chart-1", name="My Chart", chart_type="line")
    calls = []

    def spy_migrate_chart(raw, schema_version):
        calls.append(schema_version)
        return raw

    with patch("pandaplot.storage.chart_data_manager.migrate_chart", side_effect=spy_migrate_chart):
        _round_trip(chart, schema_version=0)

    assert calls == [0]
