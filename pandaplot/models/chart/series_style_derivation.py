"""Bridges DataSeries's flat fields to a typed SeriesStyleBase object,
read fresh from the series' CURRENT flat field values every call.

Deliberately does not read DataSeries.style: nothing populates or
refreshes that field for a series created or edited after Phase 3a
shipped (only the v1->v2 migration ever writes it), so it cannot yet be
trusted as authoritative. The flat fields remain the single source of
truth for rendering through Phase 3b; this function only changes their
*shape* (a typed object instead of loose attribute reads) for whichever
caller needs one.
"""
import dataclasses

from pandaplot.models.chart.series_style.base import SeriesStyleBase


def derive_style(series, style_cls: type[SeriesStyleBase]) -> SeriesStyleBase:
    field_names = [f.name for f in dataclasses.fields(style_cls)]
    return style_cls(**{name: getattr(series, name) for name in field_names})
