"""Tests for CHART_TYPE_SPECS, absorbing chart_role_spec.py's
CHART_ROLE_SPECS content (display_name/roles/required_roles, unchanged
values) plus the new allowed_series_types/allows_fit/default_series_type
fields from the design's allowed-series-types-per-chart-type table.
supports_error_bars is a property, not a stored field -- reconciled with
SeriesTypeSpec rather than duplicated (see chart_type_spec.py's
docstring).
"""
import pytest

from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.chart_type_spec import CHART_TYPE_SPECS, get_chart_type_spec
from pandaplot.models.chart.series_type import SeriesType


def test_all_five_chart_types_are_registered():
    assert set(CHART_TYPE_SPECS.keys()) == {
        ChartType.LINE, ChartType.SCATTER, ChartType.BAR, ChartType.HIST, ChartType.VECTOR,
    }


def test_line_spec_matches_former_chart_role_spec_values():
    spec = CHART_TYPE_SPECS[ChartType.LINE]
    assert spec.display_name == "Line"
    assert spec.roles == ("x", "y")
    assert spec.required_roles == ("y",)
    assert spec.supports_error_bars is True


def test_hist_spec_matches_former_chart_role_spec_values():
    spec = CHART_TYPE_SPECS[ChartType.HIST]
    assert spec.display_name == "Histogram"
    assert spec.roles == ("values",)
    assert spec.required_roles == ("values",)
    assert spec.supports_error_bars is False


def test_vector_spec_matches_former_chart_role_spec_values():
    spec = CHART_TYPE_SPECS[ChartType.VECTOR]
    assert spec.display_name == "Vector"
    assert spec.roles == ("x", "y", "u", "v", "magnitude")
    assert spec.required_roles == ("x", "y", "u", "v")
    assert spec.supports_error_bars is False


def test_allowed_series_types_per_chart_type():
    assert CHART_TYPE_SPECS[ChartType.LINE].allowed_series_types == {SeriesType.LINE, SeriesType.SCATTER}
    assert CHART_TYPE_SPECS[ChartType.SCATTER].allowed_series_types == {SeriesType.SCATTER}
    assert CHART_TYPE_SPECS[ChartType.BAR].allowed_series_types == {SeriesType.BAR, SeriesType.SCATTER}
    assert CHART_TYPE_SPECS[ChartType.HIST].allowed_series_types == {SeriesType.HIST}
    assert CHART_TYPE_SPECS[ChartType.VECTOR].allowed_series_types == {SeriesType.VECTOR, SeriesType.LINE}


def test_all_chart_types_allow_fit():
    assert all(spec.allows_fit for spec in CHART_TYPE_SPECS.values())


def test_default_series_type_matches_chart_type():
    # Every chart type's default series type is itself, today -- since
    # DataSeries has no series_type field yet (Phase 3), a chart's type
    # IS its (only) series' type.
    for chart_type, spec in CHART_TYPE_SPECS.items():
        assert spec.default_series_type.value == chart_type.value


def test_supports_error_bars_is_computed_not_duplicated_from_series_type_spec():
    from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS

    for chart_type, spec in CHART_TYPE_SPECS.items():
        assert spec.supports_error_bars == SERIES_TYPE_SPECS[spec.default_series_type].supports_error_bars


def test_get_chart_type_spec_accepts_a_plain_string():
    spec = get_chart_type_spec("hist")
    assert spec.display_name == "Histogram"


def test_get_chart_type_spec_accepts_a_charttype_instance():
    spec = get_chart_type_spec(ChartType.VECTOR)
    assert spec.display_name == "Vector"


def test_get_chart_type_spec_raises_on_unknown_type():
    with pytest.raises(ValueError):
        get_chart_type_spec("violin")
