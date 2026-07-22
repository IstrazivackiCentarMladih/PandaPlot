"""
Types and metadata for guided statistical hypothesis testing.

This module defines the catalog of supported statistical tests together with
the metadata the guided UI needs to render inputs and help text, plus the
result container used to surface test output in the application as data.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple

import pandas as pd


class StatTestType(Enum):
    """Supported statistical tests."""

    ONE_SAMPLE_T = "one_sample_t"
    INDEPENDENT_T = "independent_t"
    PAIRED_T = "paired_t"
    MANN_WHITNEY = "mann_whitney"
    WILCOXON = "wilcoxon"
    ONE_WAY_ANOVA = "one_way_anova"
    KRUSKAL_WALLIS = "kruskal_wallis"
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    SHAPIRO = "shapiro"


class InputMode(Enum):
    """How many columns a test consumes."""

    ONE = "one"  # A single sample column
    TWO = "two"  # Two sample columns (A and B)
    MANY = "many"  # Two or more group columns


class Alternative(Enum):
    """Alternative hypothesis direction."""

    TWO_SIDED = "two-sided"
    LESS = "less"
    GREATER = "greater"


@dataclass
class StatTestInfo:
    """Static metadata describing a statistical test for the guided UI."""

    test_type: StatTestType
    label: str
    input_mode: InputMode
    # Which optional parameters the test consumes.
    uses_alternative: bool = False
    uses_popmean: bool = False
    uses_equal_var: bool = False
    description: str = ""
    assumptions: str = ""


# Catalog of tests grouped in a sensible order for the UI. This drives both the
# combo box and the dynamic input/parameter widgets in the statistics panel.
STAT_TESTS: Dict[StatTestType, StatTestInfo] = {
    StatTestType.ONE_SAMPLE_T: StatTestInfo(
        test_type=StatTestType.ONE_SAMPLE_T,
        label="One-sample t-test",
        input_mode=InputMode.ONE,
        uses_alternative=True,
        uses_popmean=True,
        description="Tests whether the mean of a single sample differs from a known/expected value.",
        assumptions="Sample is approximately normally distributed; observations are independent.",
    ),
    StatTestType.INDEPENDENT_T: StatTestInfo(
        test_type=StatTestType.INDEPENDENT_T,
        label="Independent (two-sample) t-test",
        input_mode=InputMode.TWO,
        uses_alternative=True,
        uses_equal_var=True,
        description="Compares the means of two independent groups.",
        assumptions="Each group is approximately normal; observations are independent. "
        "Uncheck 'equal variance' for Welch's t-test when variances differ.",
    ),
    StatTestType.PAIRED_T: StatTestInfo(
        test_type=StatTestType.PAIRED_T,
        label="Paired t-test",
        input_mode=InputMode.TWO,
        uses_alternative=True,
        description="Compares two related measurements (e.g. before/after) on the same subjects.",
        assumptions="Paired differences are approximately normal; pairs are independent.",
    ),
    StatTestType.MANN_WHITNEY: StatTestInfo(
        test_type=StatTestType.MANN_WHITNEY,
        label="Mann-Whitney U (nonparametric)",
        input_mode=InputMode.TWO,
        uses_alternative=True,
        description="Nonparametric alternative to the independent t-test; compares distributions of two groups.",
        assumptions="Observations are independent. No normality assumption required.",
    ),
    StatTestType.WILCOXON: StatTestInfo(
        test_type=StatTestType.WILCOXON,
        label="Wilcoxon signed-rank (nonparametric)",
        input_mode=InputMode.TWO,
        uses_alternative=True,
        description="Nonparametric alternative to the paired t-test for two related samples.",
        assumptions="Paired differences are symmetric. No normality assumption required.",
    ),
    StatTestType.ONE_WAY_ANOVA: StatTestInfo(
        test_type=StatTestType.ONE_WAY_ANOVA,
        label="One-way ANOVA",
        input_mode=InputMode.MANY,
        description="Tests whether the means of three or more groups are all equal.",
        assumptions="Groups are approximately normal with similar variances; observations are independent.",
    ),
    StatTestType.KRUSKAL_WALLIS: StatTestInfo(
        test_type=StatTestType.KRUSKAL_WALLIS,
        label="Kruskal-Wallis (nonparametric)",
        input_mode=InputMode.MANY,
        description="Nonparametric alternative to one-way ANOVA; compares distributions across groups.",
        assumptions="Observations are independent. No normality assumption required.",
    ),
    StatTestType.PEARSON: StatTestInfo(
        test_type=StatTestType.PEARSON,
        label="Pearson correlation",
        input_mode=InputMode.TWO,
        uses_alternative=True,
        description="Measures the strength of a linear relationship between two variables.",
        assumptions="Relationship is linear; both variables are approximately normal.",
    ),
    StatTestType.SPEARMAN: StatTestInfo(
        test_type=StatTestType.SPEARMAN,
        label="Spearman correlation (rank)",
        input_mode=InputMode.TWO,
        uses_alternative=True,
        description="Measures the strength of a monotonic (rank-based) relationship between two variables.",
        assumptions="Relationship is monotonic. No normality assumption required.",
    ),
    StatTestType.SHAPIRO: StatTestInfo(
        test_type=StatTestType.SHAPIRO,
        label="Shapiro-Wilk normality test",
        input_mode=InputMode.ONE,
        description="Tests whether a sample was drawn from a normally distributed population.",
        assumptions="Observations are independent. Best for small-to-moderate sample sizes.",
    ),
}


@dataclass
class StatTestResult:
    """Result of a statistical test, ready to be shown as data."""

    test_type: StatTestType
    test_name: str
    source_columns: List[str]
    statistic: float
    p_value: float
    alpha: float
    # Ordered (metric, value) pairs shown as the results table.
    rows: List[Tuple[str, Any]] = field(default_factory=list)
    conclusion: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def significant(self) -> bool:
        """Whether the result is significant at the chosen alpha level."""
        return self.p_value is not None and self.p_value < self.alpha

    def to_dataframe(self) -> pd.DataFrame:
        """Convert the result into a tidy Metric/Value table."""
        return pd.DataFrame(self.rows, columns=["Metric", "Value"])

    def result_name(self) -> str:
        """Generate a default name for the results dataset."""
        cols = ", ".join(self.source_columns)
        return f"{self.test_name} [{cols}]"
