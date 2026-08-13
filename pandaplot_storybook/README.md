# PandaPlot Storybook

An interactive PySide6 gallery for the reusable widgets in
`pandaplot/gui/components/common` — browse each one, tweak its values live,
and preview it under Light/Dark/System theme exactly as it renders in the
real app.

This is a standalone project: it depends on PandaPlot's source tree, but
PandaPlot never depends on it.

## Setup

```bash
cd pandaplot_storybook
uv sync
```

## Running

```bash
python -m pandaplot_storybook
```

## Running tests

```bash
uv run pytest
```

## Adding a new story

Add `pandaplot_storybook/stories/<widget>_story.py` with a `@story("Name")`-decorated
builder returning a `StoryDef` (see any existing `*_story.py` for the pattern),
then import it from `pandaplot_storybook/stories/__init__.py`.
