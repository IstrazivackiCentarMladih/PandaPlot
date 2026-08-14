"""Tests for the descriptive statistics engine."""

import numpy as np
import pandas as pd
import pytest

from pandaplot.analysis import DESCRIPTIVE_STATS, DescriptiveStatsEngine


def _cols(**series):
    return [pd.Series(v, name=k) for k, v in series.items()]


class TestDescriptiveStatsEngine:
    def test_basic_statistics_are_correct(self):
        result = DescriptiveStatsEngine.describe(_cols(A=[1.0, 2.0, 3.0, 4.0, 5.0]))
        by_stat = {row["Statistic"]: row["A"] for _, row in result.stats.iterrows()}

        assert by_stat[DESCRIPTIVE_STATS["count"]] == "5"
        assert by_stat[DESCRIPTIVE_STATS["missing"]] == "0"
        assert float(by_stat[DESCRIPTIVE_STATS["mean"]]) == pytest.approx(3.0)
        assert float(by_stat[DESCRIPTIVE_STATS["median"]]) == pytest.approx(3.0)
        assert float(by_stat[DESCRIPTIVE_STATS["min"]]) == pytest.approx(1.0)
        assert float(by_stat[DESCRIPTIVE_STATS["max"]]) == pytest.approx(5.0)
        assert float(by_stat[DESCRIPTIVE_STATS["range"]]) == pytest.approx(4.0)
        # Sample std of 1..5 is sqrt(2.5).
        assert float(by_stat[DESCRIPTIVE_STATS["std"]]) == pytest.approx(np.sqrt(2.5))

    def test_quartiles_and_iqr(self):
        result = DescriptiveStatsEngine.describe(_cols(A=list(range(1, 101))))
        by_stat = {row["Statistic"]: row["A"] for _, row in result.stats.iterrows()}
        q1 = float(by_stat[DESCRIPTIVE_STATS["q1"]])
        q3 = float(by_stat[DESCRIPTIVE_STATS["q3"]])
        iqr = float(by_stat[DESCRIPTIVE_STATS["iqr"]])
        assert q1 == pytest.approx(np.percentile(range(1, 101), 25))
        assert q3 == pytest.approx(np.percentile(range(1, 101), 75))
        assert iqr == pytest.approx(q3 - q1)

    def test_missing_values_are_dropped_and_counted(self):
        result = DescriptiveStatsEngine.describe(_cols(A=[1.0, np.nan, 3.0, np.nan, 5.0]))
        by_stat = {row["Statistic"]: row["A"] for _, row in result.stats.iterrows()}
        assert by_stat[DESCRIPTIVE_STATS["count"]] == "3"
        assert by_stat[DESCRIPTIVE_STATS["missing"]] == "2"
        assert float(by_stat[DESCRIPTIVE_STATS["mean"]]) == pytest.approx(3.0)

    def test_multiple_columns_produce_one_column_each(self):
        result = DescriptiveStatsEngine.describe(_cols(A=[1.0, 2.0, 3.0], B=[10.0, 20.0, 30.0]))
        assert result.source_columns == ["A", "B"]
        assert list(result.stats.columns) == ["Statistic", "A", "B"]
        assert len(result.stats) == len(DESCRIPTIVE_STATS)

    def test_single_value_leaves_sample_stats_na(self):
        result = DescriptiveStatsEngine.describe(_cols(A=[42.0]))
        by_stat = {row["Statistic"]: row["A"] for _, row in result.stats.iterrows()}
        assert by_stat[DESCRIPTIVE_STATS["count"]] == "1"
        assert float(by_stat[DESCRIPTIVE_STATS["mean"]]) == pytest.approx(42.0)
        # Sample std/variance are undefined for a single observation.
        assert by_stat[DESCRIPTIVE_STATS["std"]] == "n/a"
        assert by_stat[DESCRIPTIVE_STATS["skewness"]] == "n/a"

    def test_non_numeric_column_is_reported_as_empty(self):
        result = DescriptiveStatsEngine.describe(_cols(A=["x", "y", "z"]))
        by_stat = {row["Statistic"]: row["A"] for _, row in result.stats.iterrows()}
        assert by_stat[DESCRIPTIVE_STATS["count"]] == "0"
        assert by_stat[DESCRIPTIVE_STATS["missing"]] == "3"

    def test_empty_columns_raises(self):
        with pytest.raises(ValueError):
            DescriptiveStatsEngine.describe([])

    def test_report_mentions_columns_and_stats(self):
        result = DescriptiveStatsEngine.describe(_cols(Temp=[1.0, 2.0, 3.0, 4.0, 5.0]))
        report = result.report()
        assert "Descriptive Statistics Report" in report
        assert "Temp" in report
        assert "Mean" in report
        # The report should be non-trivial Markdown with a table.
        assert "|" in report
