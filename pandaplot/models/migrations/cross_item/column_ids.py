"""Cross-item migration: backfill column ids on chart series/fits.

Legacy projects (and any references saved with an empty id) stored
column references by name only. Now that datasets are loaded and carry
a column-id registry, resolve each reference's name to a stable id so a
later column rename doesn't break the reference. assign_* only fills
ids for names that still match a column; unmatched names keep an empty
id and fall back to the name at resolve time.

Runs against a fully-instantiated Project (all items loaded and added to
the tree), not a raw dict, because it needs to look up each series'
source Dataset by id — data that isn't available from one item's raw
dict in isolation. See migrations/per_item/ for the pure dict -> dict
counterpart used when a migration doesn't need another item's data.
"""
from pandaplot.models.project.items.chart import (
    Chart,
    assign_fit_column_ids,
    assign_series_column_ids,
)
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project


def migrate_column_ids(project: Project) -> None:
    for item in project.get_all_items():
        if not isinstance(item, Chart):
            continue
        for series in item.data_series:
            dataset = project.find_item(series.dataset_id)
            if isinstance(dataset, Dataset):
                assign_series_column_ids(series, dataset)
        for fit in item.fit_data:
            dataset = project.find_item(fit.source_dataset_id)
            if isinstance(dataset, Dataset):
                assign_fit_column_ids(fit, dataset)
