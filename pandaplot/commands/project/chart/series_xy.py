"""Shared (x, y) resolution for a chart's data/fit series.

Used by any command that needs the live x/y values of whichever series or
fit the user picked -- AnalyzeChartSeriesCommand and (#268)
TransformChartSeriesCommand.
"""

from typing import Literal

import numpy as np
import pandas as pd

from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart, resolve_series_column
from pandaplot.models.state import AppState

SourceKind = Literal["series", "fit"]


def resolve_series_xy(
    app_state: AppState, chart: Chart, source_kind: SourceKind, source_index: int,
) -> tuple[pd.Series, pd.Series, str, str]:
    """Return (x, y, x_label, y_label) for chart's source_kind/source_index entry.

    Raises ValueError when the series/fit no longer exists, its series type
    has no meaningful ordered (x, y) curve, or its dataset/columns are
    unavailable.
    """
    if source_kind == "fit":
        if not (0 <= source_index < len(chart.fit_data)):
            raise ValueError("Selected fit no longer exists.")
        fit = chart.fit_data[source_index]
        dataset = app_state.current_project.find_item(fit.source_dataset_id)
        if not isinstance(dataset, Dataset):
            dataset = None
        x_label = resolve_series_column(dataset, fit.source_x_column_id, fit.source_x_column) or "x"
        x = pd.Series(np.asarray(fit.x_data), dtype="float64")
        y = pd.Series(np.asarray(fit.y_data), dtype="float64")
        return x, y, x_label, fit.label

    if not (0 <= source_index < len(chart.data_series)):
        raise ValueError("Selected series no longer exists.")
    series = chart.data_series[source_index]
    if not SERIES_TYPE_SPECS[series.series_type].supports_curve_analysis:
        raise ValueError(
            f"'{series.series_type.value}' series don't support this analysis "
            "(only line, scatter, and fitted curves do)."
        )
    dataset = app_state.current_project.find_item(series.dataset_id)
    if not isinstance(dataset, Dataset) or dataset.data is None:
        raise ValueError("Series dataset is not available.")

    x_name = resolve_series_column(dataset, series.x_column_id, series.x_column)
    y_name = resolve_series_column(dataset, series.y_column_id, series.y_column)
    df = dataset.data
    if y_name is None or y_name not in df.columns:
        raise ValueError("Series y column not found.")

    if x_name and x_name in df.columns:
        x_full = df[x_name]
        x_label = x_name
    else:
        x_full = pd.Series(np.arange(len(df)), index=df.index)
        x_label = "index"
    y_full = df[y_name]

    mask = ~(pd.isna(x_full) | pd.isna(y_full))
    x = pd.to_numeric(x_full[mask], errors="coerce").reset_index(drop=True)
    y = pd.to_numeric(y_full[mask], errors="coerce").reset_index(drop=True)
    label = series.label or y_name
    return x, y, x_label, label
