"""
Example script creating a "Statistical Analysis Basics" project.

This example demonstrates core descriptive statistics, distribution
visualizations, group comparisons, and correlation analysis on a synthetic
anthropometric dataset (height, weight, age, exercise habits).
"""

import os
import sys

import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pandaplot.models.project import Project
from pandaplot.models.project.items import Chart, Dataset, Folder, Note
from pandaplot.models.project.items.chart import DataSeries
from pandaplot.storage.chart_data_manager import ChartDataManager
from pandaplot.storage.dataset_data_manager import DatasetDataManager
from pandaplot.storage.folder_data_manager import FolderDataManager
from pandaplot.storage.item_data_manager_factory import ItemDataManagerFactory
from pandaplot.storage.note_data_manager import NoteDataManager
from pandaplot.storage.project_data_manager import ProjectDataManager

N_SAMPLES = 200
RANDOM_SEED = 42


def create_project_data_manager() -> ProjectDataManager:
    """Create and configure the project data manager."""
    item_data_manager_factory = ItemDataManagerFactory()

    item_data_manager_factory.register(
        type_name="note",
        item_class=Note,
        manager=NoteDataManager(),
        extension="note"
    )

    item_data_manager_factory.register(
        type_name="folder",
        item_class=Folder,
        manager=FolderDataManager(),
        extension="folder"
    )

    item_data_manager_factory.register(
        type_name="chart",
        item_class=Chart,
        manager=ChartDataManager(),
        extension="chart"
    )

    item_data_manager_factory.register(
        type_name="dataset",
        item_class=Dataset,
        manager=DatasetDataManager(),
        extension="dataset"
    )

    project_data_manager = ProjectDataManager(item_data_manager_factory)
    return project_data_manager


def generate_anthropometric_data(n: int = N_SAMPLES, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate a synthetic dataset of height, weight, age and exercise habits.

    The relationships are deliberately built in so the correlation analysis
    later in the tutorial has something meaningful to find:
    - Height and Weight are positively correlated (taller people, on
      average, weigh more), mediated through a randomly sampled BMI.
    - Exercise hours and Weight/BMI are negatively correlated.
    - Age has only a weak effect on the other variables.
    """
    rng = np.random.default_rng(seed)

    gender = rng.choice(["Male", "Female"], size=n)

    age = rng.integers(18, 71, size=n)

    # Height depends on gender, with realistic population variance.
    height_mean = np.where(gender == "Male", 176.0, 163.0)
    height_std = np.where(gender == "Male", 7.0, 6.0)
    height_cm = rng.normal(height_mean, height_std)

    # Exercise habits (hours/week), independent of gender.
    exercise_hours_week = np.clip(rng.gamma(shape=2.0, scale=2.0, size=n), 0, 14)

    # Base BMI with a mild downward pull from exercise and upward drift with age,
    # plus random individual variation.
    base_bmi = rng.normal(24.0, 3.0, size=n)
    bmi_target = base_bmi - 0.35 * exercise_hours_week + 0.02 * (age - 40)
    bmi_target = np.clip(bmi_target, 15.5, 40.0)

    # Weight derived from the target BMI and height, with a touch of noise.
    weight_kg = bmi_target * (height_cm / 100) ** 2 + rng.normal(0, 2.0, size=n)
    weight_kg = np.clip(weight_kg, 40, 150)

    # Recompute BMI from the final height/weight so the two stay consistent.
    bmi = weight_kg / (height_cm / 100) ** 2

    data = pd.DataFrame({
        "Subject_ID": np.arange(1, n + 1),
        "Gender": gender,
        "Age": age,
        "Height_cm": np.round(height_cm, 1),
        "Weight_kg": np.round(weight_kg, 1),
        "BMI": np.round(bmi, 1),
        "Exercise_Hours_Week": np.round(exercise_hours_week, 1),
    })

    return data


def compute_descriptive_statistics(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Compute a table of common descriptive statistics for each numeric column."""
    rows = []
    for col in columns:
        series = data[col]
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        # Mode of continuous data is computed on values rounded to the nearest
        # whole unit, otherwise every value is unique and "mode" is meaningless.
        mode_value = series.round(0).mode().iloc[0]

        rows.append({
            "Variable": col,
            "Count": series.count(),
            "Mean": round(series.mean(), 2),
            "Median": round(series.median(), 2),
            "Mode": round(mode_value, 2),
            "Std_Dev": round(series.std(), 2),
            "Variance": round(series.var(), 2),
            "Min": round(series.min(), 2),
            "Max": round(series.max(), 2),
            "Range": round(series.max() - series.min(), 2),
            "Q1_25th": round(q1, 2),
            "Q3_75th": round(q3, 2),
            "IQR": round(q3 - q1, 2),
            "Skewness": round(series.skew(), 3),
            "Kurtosis": round(series.kurt(), 3),
        })

    return pd.DataFrame(rows)


def compute_group_statistics(data: pd.DataFrame, group_col: str, value_cols: list[str]) -> pd.DataFrame:
    """Compute a wide five-number-summary table per group, per variable.

    This is the same information a box plot visualizes (min, Q1, median, Q3,
    max, IQR) laid out as one row per group so it can be plotted directly.
    """
    rows = []
    # PandaPlot's bar chart tick locator currently renders numeric positions
    # rather than category text for a string x-axis, so we also provide a
    # numeric code column for charts to plot against, with the mapping
    # spelled out in the chart's axis label.
    for group_code, (group_name, group_df) in enumerate(data.groupby(group_col)):
        row = {group_col: group_name, f"{group_col}_Code": group_code}
        for col in value_cols:
            series = group_df[col]
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            row.update({
                f"{col}_Mean": round(series.mean(), 2),
                f"{col}_Median": round(series.median(), 2),
                f"{col}_Std": round(series.std(), 2),
                f"{col}_Min": round(series.min(), 2),
                f"{col}_Q1": round(q1, 2),
                f"{col}_Q3": round(q3, 2),
                f"{col}_Max": round(series.max(), 2),
                f"{col}_IQR": round(iqr, 2),
                # Whisker ends per the standard 1.5*IQR box plot rule, clipped
                # to the observed data range.
                f"{col}_Whisker_Low": round(max(series.min(), q1 - 1.5 * iqr), 2),
                f"{col}_Whisker_High": round(min(series.max(), q3 + 1.5 * iqr), 2),
            })
        rows.append(row)

    return pd.DataFrame(rows)


def compute_correlation_matrix(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Compute a Pearson correlation matrix as a plain DataFrame (row-labelled)."""
    corr = data[columns].corr(method="pearson").round(3)
    corr.insert(0, "Variable", corr.index)
    corr = corr.reset_index(drop=True)
    return corr


def create_statistics_project():
    """Create the full statistical analysis example project."""

    project = Project(
        name="Statistical Analysis Basics",
        description="A step-by-step tutorial covering descriptive statistics, "
                     "distribution visualizations, group comparisons and "
                     "correlation analysis on a synthetic height/weight/age dataset."
    )
    project_data_manager = create_project_data_manager()

    # --- Folder structure -------------------------------------------------
    raw_data_folder = Folder(name="Raw Data")
    stats_folder = Folder(name="Descriptive Statistics")
    viz_folder = Folder(name="Visualizations")
    tutorial_folder = Folder(name="Tutorial")

    project.add_item(raw_data_folder)
    project.add_item(stats_folder)
    project.add_item(viz_folder)
    project.add_item(tutorial_folder)

    # --- Data generation ----------------------------------------------------
    print("Generating synthetic anthropometric dataset...")
    data = generate_anthropometric_data()
    numeric_cols = ["Age", "Height_cm", "Weight_kg", "BMI", "Exercise_Hours_Week"]

    main_dataset = Dataset(name="Anthropometric Data", data=data)
    project.add_item(main_dataset, raw_data_folder.id)

    # Gender subsets, used later to build a colour-split scatter chart.
    male_dataset = Dataset(name="Male Subset", data=data[data["Gender"] == "Male"].reset_index(drop=True))
    female_dataset = Dataset(name="Female Subset", data=data[data["Gender"] == "Female"].reset_index(drop=True))
    project.add_item(male_dataset, raw_data_folder.id)
    project.add_item(female_dataset, raw_data_folder.id)

    # --- Statistics ----------------------------------------------------------
    print("Computing descriptive statistics...")
    summary_stats = compute_descriptive_statistics(data, numeric_cols)
    summary_dataset = Dataset(name="Summary Statistics", data=summary_stats)
    project.add_item(summary_dataset, stats_folder.id)

    print("Computing group statistics (box plot five-number summary)...")
    group_value_cols = ["Height_cm", "Weight_kg", "BMI"]
    group_stats = compute_group_statistics(data, "Gender", group_value_cols)
    group_dataset = Dataset(name="Group Statistics by Gender", data=group_stats)
    project.add_item(group_dataset, stats_folder.id)

    print("Computing correlation matrix...")
    correlation_matrix = compute_correlation_matrix(data, numeric_cols)
    correlation_dataset = Dataset(name="Correlation Matrix", data=correlation_matrix)
    project.add_item(correlation_dataset, stats_folder.id)

    # --- Charts ----------------------------------------------------------
    print("Creating charts...")

    def add_series(chart: Chart, dataset_id: str, x_col: str, y_col: str, label: str, color: str):
        chart.data_series.append(DataSeries(
            dataset_id=dataset_id,
            x_column=x_col,
            y_column=y_col,
            label=label,
            color=color,
        ))

    # 1. Histogram of Height
    height_hist = Chart(name="Height Distribution", chart_type="hist")
    height_hist.config.update({
        "title": "Height Distribution",
        "x_label": "Height (cm)",
        "y_label": "Frequency",
    })
    add_series(height_hist, main_dataset.id, "Height_cm", "Height_cm", "Height (cm)", "#1f77b4")
    project.add_item(height_hist, viz_folder.id)

    # 2. Histogram of Weight
    weight_hist = Chart(name="Weight Distribution", chart_type="hist")
    weight_hist.config.update({
        "title": "Weight Distribution",
        "x_label": "Weight (kg)",
        "y_label": "Frequency",
    })
    add_series(weight_hist, main_dataset.id, "Weight_kg", "Weight_kg", "Weight (kg)", "#ff7f0e")
    project.add_item(weight_hist, viz_folder.id)

    # 3. Histogram of BMI
    bmi_hist = Chart(name="BMI Distribution", chart_type="hist")
    bmi_hist.config.update({
        "title": "BMI Distribution",
        "x_label": "BMI",
        "y_label": "Frequency",
    })
    add_series(bmi_hist, main_dataset.id, "BMI", "BMI", "BMI", "#2ca02c")
    project.add_item(bmi_hist, viz_folder.id)

    # 4. Scatter: Height vs Weight, split by gender (colour-coded)
    height_weight_scatter = Chart(name="Height vs Weight by Gender", chart_type="scatter")
    height_weight_scatter.config.update({
        "title": "Height vs Weight by Gender",
        "x_label": "Height (cm)",
        "y_label": "Weight (kg)",
    })
    add_series(height_weight_scatter, male_dataset.id, "Height_cm", "Weight_kg", "Male", "#1f77b4")
    add_series(height_weight_scatter, female_dataset.id, "Height_cm", "Weight_kg", "Female", "#d62728")
    project.add_item(height_weight_scatter, viz_folder.id)

    # 5. Scatter: Exercise vs BMI (negative relationship)
    exercise_bmi_scatter = Chart(name="Exercise vs BMI", chart_type="scatter")
    exercise_bmi_scatter.config.update({
        "title": "Exercise Hours per Week vs BMI",
        "x_label": "Exercise (hours/week)",
        "y_label": "BMI",
    })
    add_series(exercise_bmi_scatter, main_dataset.id, "Exercise_Hours_Week", "BMI", "Subjects", "#9467bd")
    project.add_item(exercise_bmi_scatter, viz_folder.id)

    # 6. Bar: Weight IQR by gender (box-plot spread visualization)
    # Uses the numeric Gender_Code column (0 = Female, 1 = Male) rather than
    # the Gender text column: PandaPlot's bar chart axis currently renders
    # numeric tick positions rather than category text for a string x-axis.
    weight_iqr_chart = Chart(name="Weight IQR by Gender (Box Plot Spread)", chart_type="bar")
    weight_iqr_chart.config.update({
        "title": "Weight IQR by Gender (Box Plot Spread)",
        "x_label": "Gender (0 = Female, 1 = Male)",
        "y_label": "Interquartile Range of Weight (kg)",
    })
    add_series(weight_iqr_chart, group_dataset.id, "Gender_Code", "Weight_kg_IQR", "Weight IQR", "#8c564b")
    project.add_item(weight_iqr_chart, viz_folder.id)

    # 7. Bar: Weight median by gender
    weight_median_chart = Chart(name="Weight Median by Gender", chart_type="bar")
    weight_median_chart.config.update({
        "title": "Weight Median by Gender",
        "x_label": "Gender (0 = Female, 1 = Male)",
        "y_label": "Median Weight (kg)",
    })
    add_series(weight_median_chart, group_dataset.id, "Gender_Code", "Weight_kg_Median", "Median Weight", "#e377c2")
    project.add_item(weight_median_chart, viz_folder.id)

    # --- Tutorial notes ----------------------------------------------------
    print("Writing tutorial notes...")
    create_tutorial_notes(
        project, tutorial_folder.id,
        data=data,
        numeric_cols=numeric_cols,
        summary_stats=summary_stats,
        group_stats=group_stats,
        correlation_matrix=correlation_matrix,
    )

    # --- Save ----------------------------------------------------------
    project_file = os.path.join(os.path.dirname(__file__), "statistics_basics.pplot")
    project_data_manager.save(project, project_file)

    print(f"\nStatistics example project created and saved to: {project_file}")
    print("\nProject structure:")
    print_project_structure(project, project.root.id, 0)

    return project


def create_tutorial_notes(project, tutorial_folder_id, *, data, numeric_cols,
                           summary_stats, group_stats, correlation_matrix):
    """Create the step-by-step tutorial notes, with real computed numbers embedded."""

    # --- 01: Introduction ------------------------------------------------
    intro = Note(name="01 - Introduction & Dataset Overview")
    intro.content = f"""# Introduction & Dataset Overview

This project is a hands-on tutorial for basic statistical analysis in PandaPlot.
It walks through descriptive statistics, distribution visualizations, group
comparisons and correlation analysis using a synthetic dataset of human body
measurements.

## The Dataset

The **Anthropometric Data** dataset (in *Raw Data*) contains {len(data)} synthetic
subjects with the following columns:

| Column | Description | Unit |
|---|---|---|
| Subject_ID | Unique identifier | - |
| Gender | Male / Female | - |
| Age | Age of subject | years |
| Height_cm | Height | centimeters |
| Weight_kg | Weight | kilograms |
| BMI | Body Mass Index, weight / height² | kg/m² |
| Exercise_Hours_Week | Self-reported exercise | hours/week |

The data is randomly generated (with a fixed random seed, so it's reproducible)
but built with realistic relationships baked in:
- Taller subjects tend to weigh more (Height and Weight are positively correlated).
- Subjects who exercise more tend to have a lower BMI (a negative correlation).
- Age has only a weak effect on the other variables.

You'll rediscover these relationships yourself in the **Correlation Analysis**
note using nothing but the data.

## How This Project Is Organized

- **Raw Data** — the base dataset plus two gender subsets (used for the
  colour-split scatter chart).
- **Descriptive Statistics** — computed summary tables (mean, median, mode,
  standard deviation, quartiles, correlation matrix, etc.).
- **Visualizations** — histograms, scatter plots and bar charts built from
  the tables above.
- **Tutorial** — this folder, with one note per step. Read them in order
  (01, 02, 03, ...).

## Recreating This Project

Everything here — the dataset, the statistics tables and the notes text
itself — was generated by `create_statistics_example.py`. Run it again with
`python create_statistics_example.py` to regenerate the project from scratch,
or edit it to explore your own synthetic variables.
"""
    project.add_item(intro, tutorial_folder_id)

    # --- 02: Descriptive statistics --------------------------------------
    height_row = summary_stats[summary_stats["Variable"] == "Height_cm"].iloc[0]
    weight_row = summary_stats[summary_stats["Variable"] == "Weight_kg"].iloc[0]

    stats_note = Note(name="02 - Descriptive Statistics")
    stats_note.content = f"""# Descriptive Statistics

The **Summary Statistics** dataset (in *Descriptive Statistics*) contains one
row per numeric variable, with all the standard descriptive statistics computed
using pandas. Here's what each column means, illustrated with the real
**Height_cm** and **Weight_kg** results:

| Statistic | What it tells you | Height (cm) | Weight (kg) |
|---|---|---|---|
| Mean | The arithmetic average | {height_row['Mean']} | {weight_row['Mean']} |
| Median | The middle value when sorted (50th percentile) | {height_row['Median']} | {weight_row['Median']} |
| Mode | The most frequently occurring value (computed on values rounded to whole units) | {height_row['Mode']} | {weight_row['Mode']} |
| Std_Dev | Standard deviation — typical distance from the mean | {height_row['Std_Dev']} | {weight_row['Std_Dev']} |
| Variance | Std_Dev squared | {height_row['Variance']} | {weight_row['Variance']} |
| Min / Max | Smallest / largest observed value | {height_row['Min']} / {height_row['Max']} | {weight_row['Min']} / {weight_row['Max']} |
| Range | Max − Min | {height_row['Range']} | {weight_row['Range']} |
| Q1_25th | 25th percentile — a quarter of subjects fall below this | {height_row['Q1_25th']} | {weight_row['Q1_25th']} |
| Q3_75th | 75th percentile — three quarters of subjects fall below this | {height_row['Q3_75th']} | {weight_row['Q3_75th']} |
| IQR | Interquartile range (Q3 − Q1) — spread of the middle 50% | {height_row['IQR']} | {weight_row['IQR']} |
| Skewness | Asymmetry of the distribution (0 = symmetric) | {height_row['Skewness']} | {weight_row['Skewness']} |
| Kurtosis | "Tailedness" relative to a normal distribution (0 = normal-like) | {height_row['Kurtosis']} | {weight_row['Kurtosis']} |

## How It Was Computed

Each row of the table comes from a handful of pandas calls on the column:

```python
series.mean()
series.median()
series.round(0).mode().iloc[0]   # mode on rounded values
series.std()
series.var()
series.quantile(0.25)   # Q1
series.quantile(0.75)   # Q3
series.skew()
series.kurt()
```

## Reading the Numbers

Mean ({height_row['Mean']} cm) and median ({height_row['Median']} cm) for
height are close together, which is a first sign the distribution is roughly
symmetric — confirmed by a skewness close to 0 ({height_row['Skewness']}).
Compare this to Weight, where mean and median differ slightly more
({weight_row['Mean']} vs {weight_row['Median']}), hinting at a touch of
right-skew from the BMI-driven weight formula used to generate the data.

Continue to **03 - Visualizing Distributions** to see these numbers as charts.
"""
    project.add_item(stats_note, tutorial_folder_id)

    # --- 03: Visualizing distributions ------------------------------------
    bmi_skew = summary_stats[summary_stats["Variable"] == "BMI"].iloc[0]["Skewness"]
    bmi_skew_desc = "right-skewed" if bmi_skew > 0.1 else "left-skewed" if bmi_skew < -0.1 else "close to symmetric"

    dist_note = Note(name="03 - Visualizing Distributions")
    dist_note.content = f"""# Visualizing Distributions

The *Visualizations* folder contains three histograms, generated with
`chart_type = "hist"`:

- **Height Distribution** — plots `Height_cm` from the main dataset.
- **Weight Distribution** — plots `Weight_kg`.
- **BMI Distribution** — plots `BMI`.

## What a Histogram Shows

A histogram bins a numeric column into equal-width intervals and counts how
many observations fall in each bin. It's the fastest way to see:

- **Central tendency** — where most of the bars are concentrated (compare
  against the Mean/Median from the previous note).
- **Spread** — how wide the range of bars is (compare against Std_Dev/IQR).
- **Shape** — symmetric vs skewed, single-peaked (unimodal) vs multi-peaked.

## Creating One Yourself

In PandaPlot, a histogram is just a chart with one data series where the
`x_column` and `y_column` both point at the variable you want to bin (the
x column is required by the chart editor but ignored by the histogram
renderer, which bins the y column):

```python
from pandaplot.models.project.items.chart import DataSeries

hist_chart = Chart(name="Height Distribution", chart_type="hist")
hist_chart.data_series.append(DataSeries(
    dataset_id=main_dataset.id,
    x_column="Height_cm",
    y_column="Height_cm",
    label="Height (cm)",
))
```

## What to Look For

The Height and Weight histograms should each look like a single bell-shaped
hump (they were generated from normal-ish distributions per gender). The BMI
histogram should look {bmi_skew_desc} — a direct visual echo of its skewness
value ({bmi_skew}) from the Descriptive Statistics table.

Continue to **04 - Relationships & Box Plots** for scatter plots and
group comparisons.
"""
    project.add_item(dist_note, tutorial_folder_id)

    # --- 04: Relationships and box plots ------------------------------------
    male_row = group_stats[group_stats["Gender"] == "Male"].iloc[0]
    female_row = group_stats[group_stats["Gender"] == "Female"].iloc[0]

    rel_note = Note(name="04 - Relationships & Box Plots")
    rel_note.content = f"""# Relationships & Box Plots

## Scatter Plots

Two scatter charts explore relationships between variables:

- **Height vs Weight by Gender** — two data series (Male in blue, Female in
  red), each pointing at a filtered dataset (`Male Subset` / `Female Subset`).
  This is the standard way to colour-split a scatter plot in PandaPlot: since
  a chart series plots one dataset's columns, you filter the rows into
  separate datasets first, then add one series per group.
- **Exercise vs BMI** — a single series over the full dataset, showing the
  downward trend between exercise hours and BMI baked into the data
  generator.

A scatter plot's job is to make covariation visible before you compute a
correlation coefficient: look for an upward trend (positive correlation), a
downward trend (negative correlation), or a shapeless cloud (no linear
relationship).

## Box Plots (as an IQR / Median Comparison)

A classic box plot draws, per group, a box from Q1 to Q3 (the IQR) with a
line at the median and "whiskers" out to `Q1 - 1.5*IQR` / `Q3 + 1.5*IQR`.
The **Group Statistics by Gender** dataset computes exactly those five
numbers per gender, per variable:

| Gender | Weight Min | Weight Q1 | Weight Median | Weight Q3 | Weight Max | Weight IQR |
|---|---|---|---|---|---|---|
| Male | {male_row['Weight_kg_Min']} | {male_row['Weight_kg_Q1']} | {male_row['Weight_kg_Median']} | {male_row['Weight_kg_Q3']} | {male_row['Weight_kg_Max']} | {male_row['Weight_kg_IQR']} |
| Female | {female_row['Weight_kg_Min']} | {female_row['Weight_kg_Q1']} | {female_row['Weight_kg_Median']} | {female_row['Weight_kg_Q3']} | {female_row['Weight_kg_Max']} | {female_row['Weight_kg_IQR']} |

The **Weight IQR by Gender** and **Weight Median by Gender** bar charts plot
the two most important numbers from that table directly — the box's height
(spread) and its centre line (median) — so you can compare the groups at a
glance even without a dedicated box-plot chart type. Their x-axis shows
`Gender_Code` (0 = Female, 1 = Male) rather than the text labels, since a bar
chart's x-axis in PandaPlot currently renders as numeric positions.

## Reading the Result

Male subjects have a higher median weight than female subjects
({male_row['Weight_kg_Median']} kg vs {female_row['Weight_kg_Median']} kg),
consistent with their higher median height driving a higher weight through
the BMI relationship used to generate the data.

Continue to **05 - Correlation Analysis** to quantify these relationships
with correlation coefficients.
"""
    project.add_item(rel_note, tutorial_folder_id)

    # --- 05: Correlation analysis ------------------------------------
    def corr_value(row_var: str, col_var: str) -> float:
        row = correlation_matrix[correlation_matrix["Variable"] == row_var].iloc[0]
        return row[col_var]

    height_weight_corr = corr_value("Height_cm", "Weight_kg")
    exercise_bmi_corr = corr_value("Exercise_Hours_Week", "BMI")
    age_bmi_corr = corr_value("Age", "BMI")

    corr_table_header = "| Variable | " + " | ".join(numeric_cols) + " |"
    corr_table_sep = "|---" * (len(numeric_cols) + 1) + "|"
    corr_table_rows = []
    for _, row in correlation_matrix.iterrows():
        cells = [str(row[c]) for c in numeric_cols]
        corr_table_rows.append(f"| {row['Variable']} | " + " | ".join(cells) + " |")
    corr_table = "\n".join([corr_table_header, corr_table_sep] + corr_table_rows)

    corr_note = Note(name="05 - Correlation Analysis")
    corr_note.content = f"""# Correlation Analysis

## What Correlation Measures

The Pearson correlation coefficient `r` measures the strength and direction
of a **linear** relationship between two numeric variables. It ranges from
-1 to 1:

- **r close to +1**: strong positive relationship (as one variable goes up,
  so does the other).
- **r close to -1**: strong negative relationship (as one goes up, the other
  goes down).
- **r close to 0**: little to no linear relationship.

## The Full Correlation Matrix

Computed with a single pandas call, `data[numeric_cols].corr(method="pearson")`,
and stored as the **Correlation Matrix** dataset:

{corr_table}

## Interpreting the Key Relationships

- **Height_cm vs Weight_kg: r = {height_weight_corr}** — a strong positive
  correlation, as expected: taller subjects weigh more. This matches the
  upward trend you saw in the "Height vs Weight by Gender" scatter plot.
- **Exercise_Hours_Week vs BMI: r = {exercise_bmi_corr}** — a negative
  correlation: subjects who report more weekly exercise tend to have a lower
  BMI. This matches the downward trend in the "Exercise vs BMI" scatter plot.
- **Age vs BMI: r = {age_bmi_corr}** — close to zero, meaning age has little
  linear relationship with BMI in this dataset (by design — the data
  generator only gives age a very small effect).

## A Word of Caution

Correlation does not imply causation, and Pearson's `r` only captures
*linear* relationships — two variables can be strongly related in a
non-linear way and still show `r` close to 0. Always look at the scatter
plot alongside the coefficient before drawing conclusions.

Continue to **06 - Summary & Next Steps**.
"""
    project.add_item(corr_note, tutorial_folder_id)

    # --- 06: Summary ------------------------------------
    summary_note = Note(name="06 - Summary & Next Steps")
    summary_note.content = f"""# Summary & Next Steps

## What This Project Covered

1. **Dataset generation** — {len(data)} synthetic subjects with height,
   weight, age, BMI and exercise data, with realistic relationships built in.
2. **Descriptive statistics** — mean, median, mode, standard deviation,
   variance, min/max, range, quartiles, IQR, skewness and kurtosis for every
   numeric variable.
3. **Distribution visualizations** — histograms for Height, Weight and BMI.
4. **Group comparisons** — a five-number summary (min, Q1, median, Q3, max)
   per gender, visualized as IQR and median bar charts (the same information
   a box plot conveys).
5. **Relationship visualizations** — scatter plots for Height vs Weight
   (split by gender) and Exercise vs BMI.
6. **Correlation analysis** — a full Pearson correlation matrix, with the
   strongest relationships called out and explained.

## Ideas to Try Next

- Open `create_statistics_example.py` and change `N_SAMPLES` or the
  distribution parameters in `generate_anthropometric_data()` to see how the
  statistics and charts respond.
- Add a new numeric column (e.g. `Resting_Heart_Rate`) to the generator and
  extend `numeric_cols` to pull it into the descriptive statistics and
  correlation matrix automatically.
- Try grouping by a different categorical column instead of `Gender` in
  `compute_group_statistics()`.
- Load your own CSV as a dataset in place of the synthetic data and rerun
  the same statistics/visualization steps against real data.
"""
    project.add_item(summary_note, tutorial_folder_id)


def print_project_structure(project, item_id, indent_level):
    """Print the project structure in a tree format."""
    if item_id == project.root.id:
        print(f"📁 {project.name}")
        for item in project.root.get_items():
            print_project_structure(project, item.id, 1)
    else:
        item = project.find_item(item_id)
        if not item:
            return

        indent = "  " * indent_level
        icon = {"folder": "📁", "dataset": "📊", "chart": "📈", "note": "📝"}.get(
            item.__class__.__name__.lower(), "📄"
        )

        print(f"{indent}{icon} {item.name}")

        if hasattr(item, "get_items"):
            for child in item.get_items():
                print_project_structure(project, child.id, indent_level + 1)


if __name__ == "__main__":
    print("Creating statistical analysis basics project...")
    create_statistics_project()
    print("\nProject creation complete!")
    print("\nTo use this project:")
    print("1. Open the PandaPlot application")
    print("2. Load the 'statistics_basics.pplot' file (or find it in the Examples browser)")
    print("3. Start with the 'Tutorial' folder and read the notes in order (01 -> 06)")
