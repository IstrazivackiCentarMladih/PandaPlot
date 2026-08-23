"""Model-string-to-matplotlib-parameter lookup tables, shared by the
series_renderers/ package and chart_editor.py's fit-plotting code."""

MARKER_MAP = {
    "circle": "o", "square": "s", "triangle": "^", "diamond": "D",
    "star": "*", "plus": "+", "cross": "x", "none": "",
}

LINESTYLE_MAP = {
    "solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-.", "none": "none",
}
