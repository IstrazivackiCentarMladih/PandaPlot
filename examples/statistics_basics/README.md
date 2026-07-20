# Statistical Analysis Basics Example

This example demonstrates basic statistical analysis in PandaPlot: descriptive
statistics, distribution visualizations, group comparisons and correlation
analysis, using a synthetic dataset of human body measurements (height,
weight, age, BMI, exercise habits).

## Overview

The example generates a synthetic dataset of 200 subjects with realistic,
built-in relationships:
- Taller subjects tend to weigh more (Height and Weight are positively correlated).
- Subjects who exercise more tend to have a lower BMI (a negative correlation).
- Age has only a weak effect on the other variables.

It then computes and visualizes the same statistics a beginner statistics
course would cover, using nothing but pandas and PandaPlot's own chart types.

## Files

### `create_statistics_example.py`

The script that generates the whole project:
- **Data generation**: a synthetic anthropometric dataset with realistic
  correlations baked in (`generate_anthropometric_data`).
- **Descriptive statistics**: mean, median, mode, standard deviation,
  variance, min/max, range, quartiles, IQR, skewness and kurtosis for every
  numeric variable (`compute_descriptive_statistics`).
- **Group statistics**: a five-number summary (min, Q1, median, Q3, max) per
  gender, per variable — the same numbers a box plot draws
  (`compute_group_statistics`).
- **Correlation analysis**: a full Pearson correlation matrix
  (`compute_correlation_matrix`).
- **Charts**: histograms, scatter plots and bar charts built from the tables
  above.
- **Tutorial notes**: six step-by-step notes with the actual computed numbers
  embedded, explaining what each statistic and chart means.

## How to Use

### Regenerate the project file

```bash
cd examples/statistics_basics
python create_statistics_example.py
```

This creates (or overwrites) `statistics_basics.pplot` in this directory.

### In the PandaPlot Application

1. Open PandaPlot.
2. Load `statistics_basics.pplot` directly, or find "Statistical Analysis
   Basics" in the built-in Examples browser.
3. Open the **Tutorial** folder and read the notes in order (01 → 06).
4. Follow along in **Raw Data**, **Descriptive Statistics** and
   **Visualizations** as each note references them.

## Project Structure

```
📁 Raw Data
  📊 Anthropometric Data       (the full 200-subject dataset)
  📊 Male Subset               (filtered, used for the colour-split scatter)
  📊 Female Subset

📁 Descriptive Statistics
  📊 Summary Statistics        (mean/median/mode/std/quartiles/skew/kurtosis)
  📊 Group Statistics by Gender (box-plot five-number summary, per gender)
  📊 Correlation Matrix

📁 Visualizations
  📈 Height Distribution        (histogram)
  📈 Weight Distribution        (histogram)
  📈 BMI Distribution           (histogram)
  📈 Height vs Weight by Gender (scatter, colour-split)
  📈 Exercise vs BMI            (scatter)
  📈 Weight IQR by Gender (Box Plot Spread)  (bar)
  📈 Weight Median by Gender                 (bar)

📁 Tutorial
  📝 01 - Introduction & Dataset Overview
  📝 02 - Descriptive Statistics
  📝 03 - Visualizing Distributions
  📝 04 - Relationships & Box Plots
  📝 05 - Correlation Analysis
  📝 06 - Summary & Next Steps
```

## Statistical Concepts Demonstrated

1. **Descriptive statistics** — measures of central tendency (mean, median,
   mode) and spread (standard deviation, variance, range, IQR), plus shape
   (skewness, kurtosis).
2. **Distributions** — reading a histogram's shape, centre and spread.
3. **Group comparisons** — comparing a five-number summary (the data behind
   a box plot) across categories.
4. **Correlation analysis** — Pearson's `r`, its sign and magnitude, and why
   it should always be checked against a scatter plot.

## A Note on Box Plots

PandaPlot's chart editor currently supports `line`, `scatter`, `bar` and
`hist` chart types. Rather than a dedicated box-plot chart, this example
computes the exact numbers a box plot would draw (min, Q1, median, Q3, max,
IQR, whiskers) into the **Group Statistics by Gender** dataset, and
visualizes the two most useful ones — spread (IQR) and center (median) — as
bar charts. The full five-number summary is available in the dataset table
for anyone who wants to sketch or export a proper box plot from it.

## Customization

You can adapt this example by editing `create_statistics_example.py`:
- `N_SAMPLES` / `RANDOM_SEED`: change the dataset size or regenerate with
  different random values.
- `generate_anthropometric_data()`: change the distributions or add new
  variables (e.g. `Resting_Heart_Rate`).
- `numeric_cols`: add your new variable here so it flows automatically into
  the descriptive statistics and correlation matrix.
- `compute_group_statistics()`: group by a different categorical column
  instead of `Gender`.

## Requirements

Uses the same scientific Python stack as the rest of PandaPlot:
- NumPy: synthetic data generation
- Pandas: statistics and data management

All dependencies are listed in the project's `pyproject.toml`.
