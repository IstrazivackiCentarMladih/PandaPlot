"""
Parse options describing how to interpret a structured data file.

The :class:`ImportOptions` dataclass is the single contract shared between the
import wizard UI (which builds it interactively) and the importer service
(which turns it into a DataFrame). Keeping it a plain dataclass means the
parsing logic stays free of Qt and is easy to unit-test.
"""

from dataclasses import dataclass

# Logical file formats. These are format *families*, not file extensions:
# a ``.txt`` file is still the CSV/delimited-text family.
CSV_FORMAT = "csv"
EXCEL_FORMAT = "excel"
JSON_FORMAT = "json"

# Named delimiters offered in the wizard, mapped to the actual separator string
# passed to pandas. "Auto-detect" is handled separately (see DataImporter).
NAMED_DELIMITERS = {
    "Comma  (,)": ",",
    "Tab  (\\t)": "\t",
    "Semicolon  (;)": ";",
    "Pipe  (|)": "|",
    "Whitespace": r"\s+",
}


@dataclass
class ImportOptions:
    """
    A fully-resolved description of how to parse a data file.

    Attributes:
        file_format: One of ``CSV_FORMAT``, ``EXCEL_FORMAT``, ``JSON_FORMAT``.
        delimiter: Field separator for delimited text. May be a single
            character (``","``) or a regex such as ``r"\\s+"`` for whitespace;
            ignored for Excel/JSON.
        has_header: When True the first non-skipped row provides column names;
            when False synthetic ``Column 1..N`` names are generated.
        skip_rows: Number of leading rows to discard before the header/data
            (useful for files with title/metadata banners).
        encoding: Text encoding for delimited-text and JSON files.
        sheet_name: Worksheet to read for Excel workbooks (name or 0-based
            index); ignored for other formats.
    """

    file_format: str = CSV_FORMAT
    delimiter: str = ","
    has_header: bool = True
    skip_rows: int = 0
    encoding: str = "utf-8"
    sheet_name: "str | int" = 0
