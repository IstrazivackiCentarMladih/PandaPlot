"""Tests for ImportDataCommand's read path (_read_frames).

Covers that the wizard's parse options are honored and that multi-sheet Excel
workbooks yield one correctly-named dataset per selected sheet. The interactive
wizard and background threading are not exercised here.
"""

from unittest.mock import Mock

import pandas as pd

from pandaplot.commands.project.dataset.import_data_command import ImportDataCommand
from pandaplot.services.data_import import CSV_FORMAT, EXCEL_FORMAT, ImportOptions


def _make_command(file_path, options, name, sheets=None):
    command = ImportDataCommand(Mock())
    command.file_path = file_path
    command.import_options = options
    command.dataset_name = name
    command.selected_sheets = sheets
    return command


def test_read_frames_honors_delimiter_and_header(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("10;20;30\n40;50;60\n", encoding="utf-8")
    options = ImportOptions(file_format=CSV_FORMAT, delimiter=";", has_header=False)

    command = _make_command(str(path), options, "data")
    frames = command._read_frames()

    assert len(frames) == 1
    name, df = frames[0]
    assert name == "data"
    assert list(df.columns) == ["Column 1", "Column 2", "Column 3"]
    assert df.iloc[0].tolist() == [10, 20, 30]


def test_read_frames_single_excel_sheet_named_after_file(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"a": [1, 2]}).to_excel(writer, sheet_name="One", index=False)
        pd.DataFrame({"b": [3]}).to_excel(writer, sheet_name="Two", index=False)

    command = _make_command(str(path), ImportOptions(file_format=EXCEL_FORMAT), "book", sheets=["One"])
    frames = command._read_frames()

    assert len(frames) == 1
    assert frames[0][0] == "book"
    assert list(frames[0][1].columns) == ["a"]


def test_read_frames_multiple_excel_sheets_suffixed(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"a": [1, 2]}).to_excel(writer, sheet_name="One", index=False)
        pd.DataFrame({"b": [3]}).to_excel(writer, sheet_name="Two", index=False)
        pd.DataFrame({"c": [7, 8, 9]}).to_excel(writer, sheet_name="Three", index=False)

    command = _make_command(str(path), ImportOptions(file_format=EXCEL_FORMAT), "book", sheets=["One", "Three"])
    frames = command._read_frames()

    assert [name for name, _ in frames] == ["book - One", "book - Three"]
    assert frames[1][1].shape == (3, 1)


def test_read_frames_falls_back_to_first_sheet_when_none_selected(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Only", index=False)

    options = ImportOptions(file_format=EXCEL_FORMAT, sheet_name="Only")
    command = _make_command(str(path), options, "book", sheets=None)
    frames = command._read_frames()

    assert len(frames) == 1
    assert list(frames[0][1].columns) == ["a"]
