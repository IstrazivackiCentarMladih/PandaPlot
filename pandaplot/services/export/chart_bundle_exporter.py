"""
Chart Bundle Exporter service.

Exports a Chart item as a self-contained bundle (.zip) containing:
1. Python script (plot.py) that recreates the chart using matplotlib/pandas/numpy.
2. Data folder (data/) with narrowed CSV file(s) containing only the columns used by the chart.
3. README.md with instructions to set up a virtualenv and run the script.
4. requirements.txt pinning the necessary python packages.
"""

import logging
import os
import re
import zipfile
from typing import Any, Dict, Set

from pandaplot.models.chart.chart_type_spec import CHART_TYPE_SPECS
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS
from pandaplot.models.project.items.chart import Chart, resolve_series_column
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project

logger = logging.getLogger(__name__)

MARKER_MAP = {
    "circle": "o",
    "square": "s",
    "triangle": "^",
    "diamond": "D",
    "star": "*",
    "plus": "+",
    "cross": "x",
    "none": "",
}

LINESTYLE_MAP = {
    "solid": "-",
    "dashed": "--",
    "dotted": ":",
    "dashdot": "-.",
    "none": "none",
}


def _cm_to_inches(cm: float) -> float:
    """Convert centimeters to inches."""
    return cm / 2.54


def _sanitize_identifier(name: str) -> str:
    """Sanitize a string to be a safe Python variable / filename identifier."""
    clean = re.sub(r"[^\w]", "_", name)
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean or clean[0].isdigit():
        clean = f"ds_{clean}"
    return clean


class ChartBundleExporter:
    """
    Generates a standalone Python + data bundle (.zip archive) for a Chart.
    """

    def __init__(self, chart: Chart, project: Project):
        self.chart = chart
        self.project = project

    def export(self, zip_path: str) -> bool:
        """
        Export the chart bundle to a .zip file at `zip_path`.

        Returns True on success, False on error.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(zip_path)), exist_ok=True)

            # 1. Gather used datasets and narrow down their columns
            dataset_info_map, dataset_file_map = self._process_datasets()

            # 2. Generate Python script
            script_code = self._generate_python_script(dataset_file_map)

            # 3. Generate README.md and requirements.txt
            readme_text = self._generate_readme()
            requirements_text = self._generate_requirements()

            # 4. Write zip archive
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                # Write Python script
                zf.writestr("plot.py", script_code)

                # Write README and requirements
                zf.writestr("README.md", readme_text)
                zf.writestr("requirements.txt", requirements_text)

                # Write narrowed CSV datasets
                for dataset_id, info in dataset_info_map.items():
                    rel_path = dataset_file_map[dataset_id]
                    df_narrow = info["dataframe"]
                    csv_bytes = df_narrow.to_csv(index=False).encode("utf-8")
                    zf.writestr(rel_path, csv_bytes)

            logger.info("Successfully exported chart bundle for '%s' to %s", self.chart.name, zip_path)
            return True

        except Exception as e:
            logger.error("Failed to export chart bundle for '%s': %s", self.chart.name, e, exc_info=True)
            return False

    def _process_datasets(self) -> tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
        """
        Identify all datasets referenced by chart series and fits, extract narrowed
        DataFrames containing only used columns, and construct target CSV paths.

        Returns:
            tuple: (dataset_info_map, dataset_file_map)
                dataset_info_map: dataset_id -> {"dataset": Dataset, "columns": set[str], "dataframe": DataFrame}
                dataset_file_map: dataset_id -> "data/filename.csv"
        """
        dataset_columns: Dict[str, Set[str]] = {}

        # Collect columns used by series
        for series in self.chart.data_series:
            ds_id = series.dataset_id
            dataset = self.project.find_item(ds_id) if self.project else None
            if not isinstance(dataset, Dataset):
                continue

            if ds_id not in dataset_columns:
                dataset_columns[ds_id] = set()

            spec = SERIES_TYPE_SPECS.get(series.series_type)
            needs_x = spec.needs_x_column if spec else True

            # X & Y columns
            if needs_x:
                x_col = resolve_series_column(dataset, series.x_column_id, series.x_column)
                if x_col:
                    dataset_columns[ds_id].add(x_col)

            y_col = resolve_series_column(dataset, series.y_column_id, series.y_column)
            if y_col:
                dataset_columns[ds_id].add(y_col)

            # Error bar columns
            error_bars = getattr(series.style, "error_bars", None)
            if error_bars is not None:
                for col_id_attr, col_attr in [
                    ("x_error_column_id", "x_error_column"),
                    ("y_error_column_id", "y_error_column"),
                    ("x_error_minus_column_id", "x_error_minus_column"),
                    ("y_error_minus_column_id", "y_error_minus_column"),
                ]:
                    cid = getattr(error_bars, col_id_attr, "")
                    cname = getattr(error_bars, col_attr, "")
                    resolved = resolve_series_column(dataset, cid, cname)
                    if resolved:
                        dataset_columns[ds_id].add(resolved)

            # Vector columns
            if spec and spec.needs_secondary_columns:
                for col_id_attr, col_attr in [
                    ("u_column_id", "u_column"),
                    ("v_column_id", "v_column"),
                    ("magnitude_column_id", "magnitude_column"),
                ]:
                    cid = getattr(series.style, col_id_attr, "")
                    cname = getattr(series.style, col_attr, "")
                    resolved = resolve_series_column(dataset, cid, cname)
                    if resolved:
                        dataset_columns[ds_id].add(resolved)

            # Z column (Colormap/Heatmap)
            if spec and spec.needs_z_column:
                cid = getattr(series.style, "z_column_id", "")
                cname = getattr(series.style, "z_column", "")
                resolved = resolve_series_column(dataset, cid, cname)
                if resolved:
                    dataset_columns[ds_id].add(resolved)

        # Collect columns used by fits
        for fit in self.chart.fit_data:
            ds_id = fit.source_dataset_id
            dataset = self.project.find_item(ds_id) if self.project else None
            if not isinstance(dataset, Dataset):
                continue

            if ds_id not in dataset_columns:
                dataset_columns[ds_id] = set()

            x_col = resolve_series_column(dataset, fit.source_x_column_id, fit.source_x_column)
            if x_col:
                dataset_columns[ds_id].add(x_col)

            y_col = resolve_series_column(dataset, fit.source_y_column_id, fit.source_y_column)
            if y_col:
                dataset_columns[ds_id].add(y_col)

        # Build info and file maps
        dataset_info_map = {}
        dataset_file_map = {}

        used_filenames: Set[str] = set()

        for ds_id, cols in dataset_columns.items():
            dataset = self.project.find_item(ds_id) if self.project else None
            if not isinstance(dataset, Dataset) or dataset.data is None:
                continue

            df = dataset.data
            # Filter DataFrame to present columns in dataset.data order
            valid_cols = [c for c in df.columns if c in cols]
            if not valid_cols:
                # If no columns were explicitly resolved, keep all columns
                df_narrow = df.copy()
            else:
                df_narrow = df[valid_cols].copy()

            # Create safe CSV filename
            base_name = _sanitize_identifier(dataset.name or f"dataset_{ds_id}")
            filename = f"{base_name}.csv"
            counter = 1
            while filename in used_filenames:
                filename = f"{base_name}_{counter}.csv"
                counter += 1
            used_filenames.add(filename)

            rel_path = f"data/{filename}"
            dataset_info_map[ds_id] = {
                "dataset": dataset,
                "columns": cols,
                "dataframe": df_narrow,
            }
            dataset_file_map[ds_id] = rel_path

        return dataset_info_map, dataset_file_map

    def _generate_python_script(self, dataset_file_map: Dict[str, str]) -> str:
        """Generate the Python script that recreates the chart."""
        config = self.chart.config
        style_cfg = self.chart.style
        is_3d = CHART_TYPE_SPECS[self.chart.chart_type].is_3d
        has_secondary_y = not is_3d and any(s.y_axis == "secondary" for s in self.chart.data_series)

        lines = [
            '"""',
            f"Generated Python plot script for chart '{self.chart.name}'.",
            "Exported from PandaPlot.",
            '"""',
            "",
            "import matplotlib.pyplot as plt",
            "import numpy as np",
            "import pandas as pd",
            "",
        ]

        # 1. Load Datasets
        lines.append("# --- 1. Load Data ---")
        lines.append("datasets = {}")
        for ds_id, rel_path in dataset_file_map.items():
            dataset = self.project.find_item(ds_id) if self.project else None
            ds_name = dataset.name if dataset else ds_id
            lines.append(f"# Dataset: {ds_name}")
            lines.append(f'datasets["{ds_id}"] = pd.read_csv("{rel_path}")')
        lines.append("")

        # 2. Setup Figure and Axes
        lines.append("# --- 2. Setup Figure and Axes ---")
        width_cm = config.get("width_cm", 20.0) or 20.0
        height_cm = config.get("height_cm", 15.0) or 15.0
        dpi = config.get("dpi", 100) or 100

        width_in = _cm_to_inches(width_cm)
        height_in = _cm_to_inches(height_cm)

        fig_bg = style_cfg.get("figure_background_color", "#ffffff")
        axes_bg = style_cfg.get("axes_background_color", "#ffffff")

        lines.append(f"fig = plt.figure(figsize=({width_in:.2f}, {height_in:.2f}), dpi={dpi})")
        lines.append(f'fig.patch.set_facecolor("{fig_bg}")')

        if is_3d:
            lines.append("ax = fig.add_subplot(111, projection='3d')")
            lines.append("ax2 = None")
        else:
            lines.append("ax = fig.add_subplot(111)")
            lines.append(f'ax.set_facecolor("{axes_bg}")')
            if has_secondary_y:
                lines.append("ax2 = ax.twinx()")
            else:
                lines.append("ax2 = None")
        lines.append("")

        # 3. Render Data Series
        lines.append("# --- 3. Render Data Series ---")
        lines.append("colorbar_mappable = None")
        lines.append("colorbar_label = ''")
        lines.append("")

        for i, series in enumerate(self.chart.data_series):
            ds_id = series.dataset_id
            dataset = self.project.find_item(ds_id) if self.project else None

            lines.append(f"# Series {i + 1}: {series.label or f'Series {i + 1}'}")
            lines.append(f'df = datasets.get("{ds_id}")')
            lines.append("if df is not None:")

            # Determine axes target
            target_ax_var = "ax2" if (series.y_axis == "secondary" and has_secondary_y) else "ax"

            spec = SERIES_TYPE_SPECS.get(series.series_type)
            needs_x = spec.needs_x_column if spec else True

            # Resolve columns
            x_col = resolve_series_column(dataset, series.x_column_id, series.x_column) if needs_x else None
            y_col = resolve_series_column(dataset, series.y_column_id, series.y_column)

            if needs_x and x_col:
                lines.append(f'    x_data = df["{x_col}"] if "{x_col}" in df.columns else df.index')
            elif needs_x:
                lines.append("    x_data = df.index")

            if y_col:
                lines.append(f'    y_data = df["{y_col}"]')
            else:
                lines.append("    y_data = None")

            lines.append("    if y_data is not None:")
            alpha_val = series.alpha if series.visible else 0.3
            label_val = series.label or f"Series {i + 1}"
            style = series.style

            # Generate series-specific plotting code
            stype = series.series_type
            series_color = getattr(style, "color", "#1f77b4")
            raw_line_style = getattr(style, "line_style", "-")
            line_style_val = LINESTYLE_MAP.get(raw_line_style, raw_line_style)
            line_width_val = getattr(style, "line_width", 1.5)

            if stype == SeriesType.LINE:
                m_style = getattr(style, "marker", None)
                raw_marker = m_style.marker_style if m_style else "none"
                marker_str = MARKER_MAP.get(raw_marker, raw_marker) if raw_marker != "none" else ""
                lines.append(
                    f"        {target_ax_var}.plot(x_data, y_data, label={repr(label_val)}, "
                    f"color={repr(series_color)}, linestyle={repr(line_style_val)}, "
                    f"linewidth={line_width_val}, marker={repr(marker_str)}, "
                    f"markersize={m_style.marker_size if m_style else 6.0}, alpha={alpha_val})"
                )
                if getattr(style, "fill_enabled", False):
                    fill_color = getattr(style, "fill_color", None) or series_color
                    fill_alpha = getattr(style, "fill_alpha", 0.3)
                    lines.append(
                        f'        {target_ax_var}.fill_between(x_data, {getattr(style, "fill_base", 0.0)}, y_data, '
                        f'color={repr(fill_color)}, alpha={fill_alpha})'
                    )

            elif stype == SeriesType.SCATTER:
                m_style = getattr(style, "marker", None)
                raw_marker = m_style.marker_style if m_style else "circle"
                marker_str = MARKER_MAP.get(raw_marker, raw_marker) if raw_marker != "none" else "o"
                size_val = (m_style.marker_size ** 2) if m_style else 36.0
                lines.append(
                    f"        {target_ax_var}.scatter(x_data, y_data, label={repr(label_val)}, "
                    f"color={repr(series_color)}, marker={repr(marker_str)}, "
                    f"s={size_val}, alpha={alpha_val})"
                )

            elif stype == SeriesType.BAR:
                bar_w = getattr(style, "bar_width", 0.8)
                lines.append(
                    f"        {target_ax_var}.bar(x_data, y_data, label={repr(label_val)}, "
                    f"color={repr(series_color)}, width={bar_w}, alpha={alpha_val})"
                )

            elif stype == SeriesType.HIST:
                bins_val = config.get("hist_bins", 20)
                lines.append(
                    f"        {target_ax_var}.hist(y_data, bins={bins_val}, label={repr(label_val)}, "
                    f"color={repr(series_color)}, alpha={alpha_val})"
                )

            elif stype == SeriesType.VECTOR:
                u_col = resolve_series_column(dataset, getattr(style, "u_column_id", ""), getattr(style, "u_column", ""))
                v_col = resolve_series_column(dataset, getattr(style, "v_column_id", ""), getattr(style, "v_column", ""))
                v_color = getattr(style, "vector_color", series_color)
                if u_col and v_col:
                    lines.append(
                        f'        {target_ax_var}.quiver(x_data, y_data, df["{u_col}"], df["{v_col}"], '
                        f'color={repr(v_color)}, alpha={alpha_val})'
                    )

            elif stype == SeriesType.COLORMAP:
                z_col = resolve_series_column(dataset, getattr(style, "z_column_id", ""), getattr(style, "z_column", ""))
                if z_col:
                    cmap_val = config.get("colormap", "viridis")
                    m_style = getattr(style, "marker", None)
                    raw_marker = m_style.marker_style if m_style else "circle"
                    marker_str = MARKER_MAP.get(raw_marker, raw_marker) if raw_marker != "none" else "o"
                    size_val = (m_style.marker_size ** 2) if m_style else 36.0
                    lines.append(
                        f'        colorbar_mappable = {target_ax_var}.scatter(x_data, y_data, c=df["{z_col}"], '
                        f'cmap={repr(cmap_val)}, marker={repr(marker_str)}, s={size_val}, alpha={alpha_val})'
                    )
                    lines.append(f'        colorbar_label = {repr(config.get("colorbar_label") or z_col)}')

            elif stype == SeriesType.HEATMAP:
                z_col = resolve_series_column(dataset, getattr(style, "z_column_id", ""), getattr(style, "z_column", ""))
                if z_col:
                    cmap_val = config.get("colormap", "viridis")
                    lines.append(
                        f'        colorbar_mappable = {target_ax_var}.pcolormesh(x_data, y_data, df["{z_col}"], '
                        f'cmap={repr(cmap_val)}, alpha={alpha_val})'
                    )
                    lines.append(f'        colorbar_label = {repr(config.get("colorbar_label") or z_col)}')

            # 3D series
            elif stype in (SeriesType.SCATTER3D, SeriesType.LINE3D, SeriesType.SURFACE, SeriesType.WIREFRAME, SeriesType.BAR3D, SeriesType.TRISURF):
                z_col = resolve_series_column(dataset, getattr(style, "z_column_id", ""), getattr(style, "z_column", ""))
                if z_col:
                    lines.append(f'        z_data = df["{z_col}"]')
                    if stype == SeriesType.SCATTER3D:
                        lines.append(f"        ax.scatter(x_data, y_data, z_data, label={repr(label_val)}, alpha={alpha_val})")
                    elif stype == SeriesType.LINE3D:
                        lines.append(f"        ax.plot(x_data, y_data, z_data, label={repr(label_val)}, alpha={alpha_val})")
                    elif stype == SeriesType.SURFACE:
                        lines.append(f'        colorbar_mappable = ax.plot_surface(x_data, y_data, z_data, cmap={repr(config.get("colormap", "viridis"))}, alpha={alpha_val})')
                    elif stype == SeriesType.WIREFRAME:
                        lines.append(f"        ax.plot_wireframe(x_data, y_data, z_data, alpha={alpha_val})")
                    elif stype == SeriesType.TRISURF:
                        lines.append(f'        colorbar_mappable = ax.plot_trisurf(x_data, y_data, z_data, cmap={repr(config.get("colormap", "viridis"))}, alpha={alpha_val})')

            # Render error bars if configured
            error_bars = getattr(style, "error_bars", None)
            if error_bars is not None and error_bars.has_error_data:
                y_err_col = resolve_series_column(dataset, error_bars.y_error_column_id, error_bars.y_error_column)
                x_err_col = resolve_series_column(dataset, error_bars.x_error_column_id, error_bars.x_error_column)
                lines.append(f'        y_err = df["{y_err_col}"] if "{y_err_col}" in df.columns else None')
                lines.append(f'        x_err = df["{x_err_col}"] if "{x_err_col}" in df.columns else None')
                lines.append("        if x_err is not None or y_err is not None:")
                lines.append(
                    f'            {target_ax_var}.errorbar(x_data, y_data, xerr=x_err, yerr=y_err, '
                    f'fmt="none", ecolor={repr(error_bars.error_color or series_color)}, '
                    f'capsize={error_bars.error_cap_size}, alpha={alpha_val})'
                )

            lines.append("")

        # 4. Render Fits
        if self.chart.fit_data:
            lines.append("# --- 4. Render Fit Curves ---")
            for j, fit in enumerate(self.chart.fit_data):
                if not fit.visible:
                    continue
                label_val = fit.label or f"Fit {j + 1}"
                fit_style = fit.style
                lines.append(f"# Fit {j + 1}: {label_val}")
                lines.append(f"fit_x_{j} = np.array({fit.x_data.tolist()})")
                lines.append(f"fit_y_{j} = np.array({fit.y_data.tolist()})")
                fit_linestyle = LINESTYLE_MAP.get(fit_style.line_style, fit_style.line_style)
                lines.append(
                    f"ax.plot(fit_x_{j}, fit_y_{j}, label={repr(label_val)}, "
                    f"color={repr(fit_style.color)}, linestyle={repr(fit_linestyle)}, "
                    f"linewidth={fit_style.line_width}, alpha={fit_style.alpha})"
                )
                if (
                    fit_style.band_fill_enabled
                    and fit.confidence_lower is not None
                    and fit.confidence_upper is not None
                ):
                    lines.append(f"conf_lower_{j} = np.array({fit.confidence_lower.tolist()})")
                    lines.append(f"conf_upper_{j} = np.array({fit.confidence_upper.tolist()})")
                    band_color = fit_style.band_color or fit_style.color
                    lines.append(
                        f"ax.fill_between(fit_x_{j}, conf_lower_{j}, conf_upper_{j}, "
                        f"color={repr(band_color)}, alpha={fit_style.band_fill_alpha})"
                    )
                lines.append("")

        # 5. Apply Titles, Labels, Limits, Grid, Legend, Colorbar
        lines.append("# --- 5. Formatting & Layout ---")
        title = config.get("title", self.chart.name)
        subtitle = config.get("subtitle", "")
        if title:
            lines.append(
                f'fig.suptitle({repr(title)}, fontsize={config.get("title_font_size", 14)}, '
                f'fontweight="bold" if {config.get("title_bold", True)} else "normal", '
                f'color={repr(config.get("title_color", "#000000"))})'
            )
        if subtitle:
            lines.append(
                f'ax.set_title({repr(subtitle)}, fontsize={config.get("subtitle_font_size", 12)}, '
                f'pad={config.get("title_padding", 6.0)})'
            )

        x_label = config.get("x_label", "")
        y_label = config.get("y_label", "")
        if x_label:
            lines.append(f'ax.set_xlabel({repr(x_label)}, fontsize={config.get("x_font_size", 12)})')
        if y_label:
            lines.append(f'ax.set_ylabel({repr(y_label)}, fontsize={config.get("y_font_size", 12)})')

        if has_secondary_y:
            y2_label = config.get("y2_label", "")
            if y2_label:
                lines.append(f'ax2.set_ylabel({repr(y2_label)}, fontsize={config.get("y2_font_size", 12)})')

        if is_3d:
            z_label = config.get("z_label", "")
            if z_label:
                lines.append(f'ax.set_zlabel({repr(z_label)}, fontsize={config.get("z_font_size", 12)})')
            lines.append(f'ax.view_init(elev={config.get("view_elev", 30.0)}, azim={config.get("view_azim", -60.0)})')

        # Scales
        x_scale = config.get("x_scale", "linear")
        y_scale = config.get("y_scale", "linear")
        if x_scale != "linear":
            lines.append(f"ax.set_xscale({repr(x_scale)})")
        if y_scale != "linear":
            lines.append(f"ax.set_yscale({repr(y_scale)})")

        # Limits
        if not config.get("x_auto_limits", True):
            lines.append(f'ax.set_xlim({config.get("x_min", 0.0)}, {config.get("x_max", 1.0)})')
        if not config.get("y_auto_limits", True):
            lines.append(f'ax.set_ylim({config.get("y_min", 0.0)}, {config.get("y_max", 1.0)})')

        # Grid
        if config.get("show_grid_x", True) or config.get("show_grid_y", True):
            lines.append(f'ax.grid(True, alpha={config.get("grid_alpha", 0.3)})')

        # Colorbar
        if config.get("colorbar_show", True):
            lines.append("if colorbar_mappable is not None:")
            lines.append("    cb = fig.colorbar(colorbar_mappable, ax=ax)")
            lines.append("    if colorbar_label:")
            lines.append("        cb.set_label(colorbar_label)")

        # Legend
        if config.get("show_legend", True):
            lines.append("handles, labels = ax.get_legend_handles_labels()")
            if has_secondary_y:
                lines.append("if ax2 is not None:")
                lines.append("    h2, l2 = ax2.get_legend_handles_labels()")
                lines.append("    handles += h2")
                lines.append("    labels += l2")
            lines.append("if handles:")
            leg_pos = config.get("legend_position", "upper right")
            lines.append(f"    ax.legend(handles, labels, loc={repr(leg_pos)})")

        lines.append("plt.tight_layout()")
        lines.append('plt.savefig("chart.png", dpi=300)')
        lines.append('print("Chart saved as chart.png")')
        lines.append("plt.show()")

        return "\n".join(lines)

    def _generate_readme(self) -> str:
        """Generate README.md for the bundle."""
        return f"""# {self.chart.name} - Python Plot Bundle

This package contains Python code and dataset(s) exported from PandaPlot to recreate the chart "{self.chart.name}".

## Contents

- `plot.py`: Standalone Python script using Matplotlib and Pandas to render the chart.
- `data/`: Folder containing the CSV dataset(s) referenced by the chart series.
- `requirements.txt`: Python package requirements.
- `README.md`: Running instructions.

## Quick Start

### 1. Create a Python Virtual Environment (Recommended)

```bash
python3 -m venv venv
```

Activate the environment:
- **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```
- **Windows:**
  ```cmd
  venv\\Scripts\\activate
  ```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Run the Script

```bash
python plot.py
```

Running the script displays the interactive chart and saves an output image `chart.png`.
"""

    def _generate_requirements(self) -> str:
        """Generate requirements.txt for the bundle."""
        reqs = [
            "matplotlib>=3.8.0",
            "pandas>=2.0.0",
            "numpy>=1.24.0",
        ]
        if self.chart.fit_data:
            reqs.append("scipy>=1.10.0")
        return "\n".join(reqs) + "\n"


def export_chart_bundle(chart: Chart, project: Project, zip_path: str) -> bool:
    """Helper function to export a chart bundle."""
    exporter = ChartBundleExporter(chart, project)
    return exporter.export(zip_path)
