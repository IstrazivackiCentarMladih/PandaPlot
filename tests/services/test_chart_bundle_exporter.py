"""Tests for ChartBundleExporter service."""

import os
import zipfile

import numpy as np
import pandas as pd
import pytest

from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_style import LineSeriesStyle, ScatterSeriesStyle
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project
from pandaplot.services.export.chart_bundle_exporter import ChartBundleExporter, export_chart_bundle


@pytest.fixture
def sample_project():
    project = Project(name="Test Project")

    # Create dataset 1 with 4 columns
    df1 = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [10.0, 20.0, 15.0, 30.0],
        "err_y": [0.5, 0.5, 0.5, 0.5],
        "unused_col": [99, 99, 99, 99],
    })
    ds1 = Dataset(name="Main Dataset")
    ds1.set_data(df1)
    project.add_item(ds1)

    # Create dataset 2
    df2 = pd.DataFrame({
        "time": [0, 1, 2],
        "value": [100, 200, 150],
        "ignored": ["a", "b", "c"],
    })
    ds2 = Dataset(name="Secondary Dataset")
    ds2.set_data(df2)
    project.add_item(ds2)

    # Create chart referencing both datasets
    chart = Chart(name="Sample Chart", chart_type=ChartType.LINE)
    chart.set_labels(title="Main Title", x_label="X Axis", y_label="Y Axis")

    # Add series 1 from ds1 (line series using x, y, and err_y)
    s1 = chart.add_data_series(
        dataset_id=ds1.id,
        x_column="x",
        y_column="y",
        label="Series 1",
    )
    s1.x_column_id = ds1.column_id("x")
    s1.y_column_id = ds1.column_id("y")
    s1.style = LineSeriesStyle(color="#ff0000")
    s1.style.error_bars.y_error_column = "err_y"
    s1.style.error_bars.y_error_column_id = ds1.column_id("err_y")

    # Add series 2 from ds2 (scatter series using time and value)
    s2 = chart.add_data_series(
        dataset_id=ds2.id,
        x_column="time",
        y_column="value",
        label="Series 2",
    )
    s2.x_column_id = ds2.column_id("time")
    s2.y_column_id = ds2.column_id("value")
    s2.style = ScatterSeriesStyle(color="#00ff00")

    # Add fit data
    chart.add_fit_data(
        source_dataset_id=ds1.id,
        fit_type="linear",
        x_data=np.array([1.0, 4.0]),
        y_data=np.array([10.0, 30.0]),
        source_x_column_id=ds1.column_id("x"),
        source_y_column_id=ds1.column_id("y"),
        source_x_column="x",
        source_y_column="y",
        label="Linear Fit",
    )

    project.add_item(chart)
    return project, chart, ds1, ds2


def test_chart_bundle_exporter_creates_zip(tmp_path, sample_project):
    project, chart, ds1, ds2 = sample_project
    zip_path = str(tmp_path / "chart_export.zip")

    exporter = ChartBundleExporter(chart, project)
    success = exporter.export(zip_path)

    assert success is True
    assert os.path.exists(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        file_list = zf.namelist()
        assert "plot.py" in file_list
        assert "README.md" in file_list
        assert "requirements.txt" in file_list

        csv_files = [f for f in file_list if f.startswith("data/") and f.endswith(".csv")]
        assert len(csv_files) == 2

        # Check README content
        readme_content = zf.read("README.md").decode("utf-8")
        assert chart.name in readme_content
        assert "python plot.py" in readme_content

        # Check requirements.txt content
        req_content = zf.read("requirements.txt").decode("utf-8")
        assert "matplotlib" in req_content
        assert "pandas" in req_content
        assert "scipy" in req_content  # because chart has fit data


def test_chart_bundle_narrowed_dataset_columns(tmp_path, sample_project):
    project, chart, ds1, ds2 = sample_project
    zip_path = str(tmp_path / "narrow_test.zip")

    export_chart_bundle(chart, project, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Verify Main Dataset CSV only contains 'x', 'y', 'err_y' and NOT 'unused_col'
        ds1_csv_name = [f for f in zf.namelist() if "Main_Dataset" in f][0]
        df1_exported = pd.read_csv(zf.open(ds1_csv_name))
        assert set(df1_exported.columns) == {"x", "y", "err_y"}
        assert "unused_col" not in df1_exported.columns

        # Verify Secondary Dataset CSV only contains 'time', 'value' and NOT 'ignored'
        ds2_csv_name = [f for f in zf.namelist() if "Secondary_Dataset" in f][0]
        df2_exported = pd.read_csv(zf.open(ds2_csv_name))
        assert set(df2_exported.columns) == {"time", "value"}
        assert "ignored" not in df2_exported.columns


def test_generated_python_script_validity_and_execution(tmp_path, sample_project):
    project, chart, ds1, ds2 = sample_project
    zip_path = str(tmp_path / "exec_test.zip")
    export_chart_bundle(chart, project, zip_path)

    # Extract zip contents into tmp_path
    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    script_path = extract_dir / "plot.py"
    assert script_path.exists()

    script_code = script_path.read_text()
    assert "import matplotlib.pyplot as plt" in script_code
    assert "fig.suptitle('Main Title'" in script_code or 'fig.suptitle("Main Title"' in script_code
    assert 'plt.savefig("chart.png", dpi=300)' in script_code or "plt.savefig('chart.png', dpi=300)" in script_code

    # Execute the generated python script in a non-interactive headless matplotlib mode
    import matplotlib
    matplotlib.use("Agg")

    globals_dict = {"__file__": str(script_path)}
    # Intercept plt.show() so it doesn't block or pop up a GUI window
    import matplotlib.pyplot as plt
    old_show = plt.show
    plt.show = lambda: None

    try:
        # Change current working directory to extracted dir so relative paths 'data/*.csv' resolve
        orig_cwd = os.getcwd()
        os.chdir(extract_dir)
        try:
            exec(compile(script_code, str(script_path), "exec"), globals_dict)
            assert (extract_dir / "chart.png").exists()
        finally:
            os.chdir(orig_cwd)
    finally:
        plt.show = old_show
