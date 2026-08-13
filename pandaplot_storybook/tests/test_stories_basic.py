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


def test_card_story_builds_a_widget(qtbot):
    story_def = get_story("Card")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_color_swatch_row_story_builds_a_widget(qtbot):
    story_def = get_story("ColorSwatchRow")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_dirty_footer_story_builds_a_widget(qtbot):
    story_def = get_story("DirtyFooter")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_drop_down_combo_box_story_builds_a_widget(qtbot):
    story_def = get_story("DropDownComboBox")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_section_header_story_builds_a_widget(qtbot):
    story_def = get_story("SectionHeader")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_slider_with_spinbox_story_builds_a_widget(qtbot):
    story_def = get_story("SliderWithSpinbox")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_value_combo_box_story_builds_a_widget(qtbot):
    story_def = get_story("ValueComboBox")
    values = {control.name: control.default for control in story_def.controls}
    widget = story_def.make_widget(values, tokens={})
    assert widget is not None
    qtbot.addWidget(widget)


def test_line_style_icons_story_builds_a_widget_with_no_controls(qtbot):
    story_def = get_story("LineStyleIcons")
    assert story_def.controls == []
    widget = story_def.make_widget({}, tokens={})
    assert widget is not None
    assert widget.count() > 0
    qtbot.addWidget(widget)


def test_font_family_options_story_builds_a_widget_with_no_controls(qtbot):
    story_def = get_story("FontFamilyOptions")
    assert story_def.controls == []
    widget = story_def.make_widget({}, tokens={})
    assert widget is not None
    assert widget.count() > 0
    qtbot.addWidget(widget)
