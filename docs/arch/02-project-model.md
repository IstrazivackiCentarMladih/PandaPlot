# Project Model and Items

## Hierarchy

```
Project (ItemCollection)
└── items: List[Item | ItemCollection]
    ├── Dataset      (wraps pandas.DataFrame)
    ├── Chart        (DataSeries + FitData + ChartConfiguration)
    ├── Note         (markdown text + tags)
    └── Folder       (ItemCollection — nested container)
```

The project maintains a **flat index** (`dict[str, Item]`) alongside the hierarchy for O(1) lookup by item ID.

## Base Classes

### `Item` (`models/project/items/item.py`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID, immutable |
| `name` | `str` | User-visible label |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last modification |
| `metadata` | `dict` | Arbitrary key-value extras |

### `ItemCollection` (`models/project/items/item.py`)

Extends `Item`. Adds:
- `items: list[Item]` — ordered children
- `add_item(item)` / `remove_item(item)` / `find_item(id)` methods

## Concrete Item Types

### Dataset (`models/project/items/dataset.py`)

```
Dataset
├── dataframe: pd.DataFrame     # The actual data
├── source_file: str | None     # Original import path
└── metadata: dict              # Column descriptions etc.
```

Datasets are the primary data source for charts and analyses.

### Chart (`models/project/items/chart.py`)

```
Chart
├── chart_type: ChartType       # LINE, SCATTER, BAR, HISTOGRAM, BOX, VIOLIN
├── config: ChartConfiguration  # title, axis labels, legend, grid
├── series: list[DataSeries]    # One or more data series
└── fit_data: list[FitData]     # Attached curve fits

DataSeries
├── dataset_id: str             # Reference to a Dataset
├── x_column: str               # Column name for X axis
├── y_column: str               # Column name for Y axis
└── style: SeriesStyle          # color, line width, marker

FitData
├── fit_type: FitType           # LINEAR, QUADRATIC, EXPONENTIAL, etc.
├── parameters: list[float]     # Fitted coefficients
├── errors: list[float]         # Standard errors
├── r_squared: float            # Goodness of fit
└── series_index: int           # Which DataSeries was fitted
```

### Note (`models/project/items/note.py`)

```
Note
├── content: str                # Raw markdown text
└── tags: list[str]             # User-defined tags
```

### Folder (`models/project/items/folder.py`)

Extends `ItemCollection` — a named container that can hold any item type, enabling nested project organization.

## Project Class (`models/project/project.py`)

```
Project
├── root: ItemCollection        # Top-level container
├── _index: dict[str, Item]     # Flat lookup by ID
├── add_item(item, parent_id?)  # Adds to root or specified parent
├── remove_item(item_id)        # Removes from hierarchy + index
├── find_item(item_id)          # O(1) lookup
└── all_items()                 # Flat iterator over all items
```

## Item Lifecycle Events

| Event | Trigger |
|-------|---------|
| `project.item_added` | Any `add_item()` call |
| `project.item_removed` | Any `remove_item()` call |
| `project.item_renamed` | `RenameItemCommand` execution |
| `dataset.created` | `ImportCsvCommand` / `CreateEmptyDatasetCommand` |
| `chart.created` | `CreateChartCommand` |
| `note.created` | Note creation command |
