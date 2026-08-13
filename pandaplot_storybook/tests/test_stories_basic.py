import pandaplot_storybook.stories  # noqa: F401  (registers all stories)
from pandaplot_storybook.registry import get_story


def test_p_button_story_builds_a_widget(qtbot):
    story_def = get_story("PButton")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_toggle_switch_story_builds_a_widget(qtbot):
    story_def = get_story("ToggleSwitch")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_segmented_control_story_builds_a_widget(qtbot):
    story_def = get_story("SegmentedControl")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_chip_row_story_builds_a_widget(qtbot):
    story_def = get_story("ChipRow")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)
