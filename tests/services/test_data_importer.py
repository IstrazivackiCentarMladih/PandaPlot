"""Tests for the structured-data import service (format/delimiter/header
detection and DataFrame parsing)."""

import json

import pandas as pd
import pytest

from pandaplot.services.data_import import (
    CSV_FORMAT,
    EXCEL_FORMAT,
    JSON_FORMAT,
    ImportOptions,
    UnsupportedFileError,
    data_importer,
    default_options,
    detect_format,
    detect_has_header,
    is_supported,
    read_dataframe,
    sniff_delimiter,
)

# --------------------------------------------------------------------- fixtures


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,age,score\nAlice,30,9.5\nBob,25,7.2\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def tsv_file(tmp_path):
    path = tmp_path / "data.tsv"
    path.write_text("name\tage\tscore\nAlice\t30\t9.5\nBob\t25\t7.2\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def semicolon_file(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name;age;score\nAlice;30;9.5\nBob;25;7.2\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def headerless_file(tmp_path):
    path = tmp_path / "nohdr.csv"
    path.write_text("1,2,3\n4,5,6\n7,8,9\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def excel_file(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_excel(writer, sheet_name="First", index=False)
        pd.DataFrame({"x": [9]}).to_excel(writer, sheet_name="Second", index=False)
    return str(path)


@pytest.fixture
def json_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]), encoding="utf-8")
    return str(path)


# ----------------------------------------------------------------- format detect


def test_detect_format_by_extension(csv_file, tsv_file, excel_file, json_file):
    assert detect_format(csv_file) == CSV_FORMAT
    assert detect_format(tsv_file) == CSV_FORMAT
    assert detect_format(excel_file) == EXCEL_FORMAT
    assert detect_format(json_file) == JSON_FORMAT


def test_detect_format_unsupported(tmp_path):
    path = tmp_path / "thing.parquet"
    path.write_text("x")
    assert is_supported(str(path)) is False
    with pytest.raises(UnsupportedFileError):
        detect_format(str(path))


# -------------------------------------------------------------- delimiter sniff


def test_sniff_delimiter_comma(csv_file):
    assert sniff_delimiter(csv_file) == ","


def test_sniff_delimiter_tab(tsv_file):
    assert sniff_delimiter(tsv_file) == "\t"


def test_sniff_delimiter_semicolon(semicolon_file):
    assert sniff_delimiter(semicolon_file) == ";"


# ----------------------------------------------------------------- header detect


def test_detect_has_header_true_for_text_header(csv_file):
    assert detect_has_header(csv_file, ",") is True


def test_detect_has_header_false_for_all_numeric(headerless_file):
    assert detect_has_header(headerless_file, ",") is False


# ----------------------------------------------------------------- default opts


def test_default_options_csv(csv_file):
    options = default_options(csv_file)
    assert options.file_format == CSV_FORMAT
    assert options.delimiter == ","
    assert options.has_header is True


def test_default_options_excel_picks_first_sheet(excel_file):
    options = default_options(excel_file)
    assert options.file_format == EXCEL_FORMAT
    assert options.sheet_name == "First"


# ------------------------------------------------------------------ read csv/tsv


def test_read_csv_with_header(csv_file):
    df = read_dataframe(csv_file, default_options(csv_file))
    assert list(df.columns) == ["name", "age", "score"]
    assert df.shape == (2, 3)
    assert df["age"].tolist() == [30, 25]


def test_read_tsv(tsv_file):
    df = read_dataframe(tsv_file, default_options(tsv_file))
    assert list(df.columns) == ["name", "age", "score"]
    assert df.shape == (2, 3)


def test_read_headerless_generates_column_names(headerless_file):
    options = ImportOptions(file_format=CSV_FORMAT, delimiter=",", has_header=False)
    df = read_dataframe(headerless_file, options)
    assert list(df.columns) == ["Column 1", "Column 2", "Column 3"]
    assert df.shape == (3, 3)


def test_read_csv_custom_delimiter(semicolon_file):
    options = ImportOptions(file_format=CSV_FORMAT, delimiter=";", has_header=True)
    df = read_dataframe(semicolon_file, options)
    assert list(df.columns) == ["name", "age", "score"]
    assert df.shape == (2, 3)


def test_read_csv_whitespace_delimiter(tmp_path):
    path = tmp_path / "ws.txt"
    path.write_text("a b c\n1 2 3\n4 5 6\n", encoding="utf-8")
    options = ImportOptions(file_format=CSV_FORMAT, delimiter=r"\s+", has_header=True)
    df = read_dataframe(str(path), options)
    assert list(df.columns) == ["a", "b", "c"]
    assert df.shape == (2, 3)


def test_read_csv_nrows_limits_preview(csv_file):
    df = read_dataframe(csv_file, default_options(csv_file), nrows=1)
    assert df.shape[0] == 1


def test_read_csv_skip_rows(tmp_path):
    path = tmp_path / "banner.csv"
    path.write_text("# exported report\n# 2026\nname,age\nAlice,30\n", encoding="utf-8")
    options = ImportOptions(file_format=CSV_FORMAT, delimiter=",", has_header=True, skip_rows=2)
    df = read_dataframe(str(path), options)
    assert list(df.columns) == ["name", "age"]
    assert df.shape == (1, 2)


def test_read_csv_encoding_fallback(tmp_path):
    path = tmp_path / "latin.csv"
    # 'é' encoded as latin-1 is not valid UTF-8; reader must fall back.
    path.write_bytes("city,temp\nMontr\xe9al,10\n".encode("latin-1"))
    options = ImportOptions(file_format=CSV_FORMAT, delimiter=",", has_header=True, encoding="utf-8")
    df = read_dataframe(str(path), options)
    assert df.shape == (1, 2)
    assert "Montr" in df.iloc[0, 0]


# ---------------------------------------------------------------------- excel


def test_read_excel_default_sheet(excel_file):
    df = read_dataframe(excel_file, default_options(excel_file))
    assert list(df.columns) == ["a", "b"]
    assert df.shape == (2, 2)


def test_read_excel_named_sheet(excel_file):
    options = ImportOptions(file_format=EXCEL_FORMAT, sheet_name="Second")
    df = read_dataframe(excel_file, options)
    assert list(df.columns) == ["x"]
    assert df.iloc[0, 0] == 9


def test_list_excel_sheets(excel_file):
    assert data_importer.list_excel_sheets(excel_file) == ["First", "Second"]


# ----------------------------------------------------------------------- json


def test_read_json_records(json_file):
    df = read_dataframe(json_file, default_options(json_file))
    assert set(df.columns) == {"a", "b"}
    assert df.shape == (2, 2)


def test_read_json_lines(tmp_path):
    path = tmp_path / "lines.json"
    path.write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
    df = read_dataframe(str(path), default_options(str(path)))
    assert df["a"].tolist() == [1, 2]
